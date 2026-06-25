from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

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
from core.run_authority_contract_templates import build_deterministic_contract
from core.run_authority_sufficiency import (
    RunSufficiencyDecision,
    RunSufficiencyJudgmentInput,
    SufficiencyPosture,
)
from core.run_authority_sufficiency_adapter import build_sufficiency_judgment_input_from_runtime
from core.run_authority_sufficiency_validation import build_deterministic_sufficiency_judgment
from core.run_kernel import RunKernel, RunStageStatus
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
from core.sufficiency_semantic_state_consumption_runtime import (
    SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION,
    build_semantic_state_facts_for_sufficiency,
    evaluate_semantic_sufficiency_overlay,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "sufficiency_semantic_state_consumption_runtime.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

RUN_ID = "run:sem-09-offline"
REQUEST_ID = "request:sem-09"
COMPONENT_ID = "component:reported-total"
EVIDENCE_ID = "evidence:public-record-notice"
COVERAGE_RECORD_ID = "coverage:reported-total"
AMENDMENT_RECORD_ID = "amendment:reported-total-caveat"


def _contract() -> dict[str, Any]:
    return build_deterministic_contract(
        query="What is the current official filing fee?",
        mode="Balanced",
    ).to_projection()


def _ledger_projection(
    contract: dict[str, Any],
    *,
    satisfied: bool = True,
    semantic_candidate_disposition: str = "accepted",
    include_semantic_candidate: bool = True,
) -> dict[str, Any]:
    from core.evidence_ledger import (
        CandidateDisposition,
        EvidenceLedger,
        build_evidence_ledger_observation_from_run_contract,
    )

    candidate = {
        "candidate_id": "C1",
        "url": "https://example.gov/rule",
        "title": "Official rule",
        "source_class": "official_current_rules",
        "source_tier": "official",
        "currentness_signal": "current",
        "readable_status": "readable",
        "fetchable_status": "fetchable",
        "disposition": CandidateDisposition.ACCEPTED.value,
        "eligible_for_stronger_obligation": True,
    }
    links = [
        {
            "requirement_id": requirement["requirement_id"],
            "candidate_id": "C1",
            "link_status": "fixture_link",
        }
        for requirement in contract["source_requirements"]
    ]
    ledger = EvidenceLedger()
    ledger.reduce_observation(
        build_evidence_ledger_observation_from_run_contract(
            observation_id="ag-sem-09:ledger:contract",
            contract_projection=contract,
        ).to_dict()
    )
    if satisfied:
        ledger.reduce_observation(
            {
                "observation_id": "ag-sem-09:ledger:candidates",
                "observation_source": "ag_sem_09_fixture",
                "candidates": [candidate],
                "requirement_links": links,
            }
        )
    if include_semantic_candidate:
        ledger.reduce_observation(
            {
                "observation_id": "ag-sem-09:ledger:semantic-coverage-candidate",
                "observation_source": "ag_sem_09_fixture",
                "candidates": [
                    {
                        "candidate_id": EVIDENCE_ID,
                        "url": "https://example.org/public-record-notice",
                        "title": "Public record notice",
                        "source_class": "primary_source_documents",
                        "source_tier": "primary",
                        "currentness_signal": "current",
                        "readable_status": "readable",
                        "fetchable_status": "fetchable",
                        "disposition": semantic_candidate_disposition,
                        "record_kind": "fact",
                        "eligible_for_stronger_obligation": True,
                        "final_evidence_eligible": True,
                    }
                ],
            }
        )
    return ledger.to_projection().to_dict()


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
    from core.run_kernel import Observation, ObservationType

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


def _seed_evidence_ledger(kernel: RunKernel) -> None:
    kernel.state.evidence_ledger.reduce_observation(
        {
            "observation_id": f"evidence-seed:{EVIDENCE_ID}",
            "observation_source": "offline_fixture",
            "candidates": [
                {
                    "candidate_id": EVIDENCE_ID,
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


def _admit(kernel: RunKernel, accepted: dict[str, object]) -> tuple[SemanticObservation, SanitizedContentReference]:
    from core.run_kernel import Observation, ObservationType

    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    component_ref = accepted["accepted_answer_component_refs"][0]
    action = kernel.authorize_semantic_observation_admission(
        semantic_observation_id=observation.observation_id,
        semantic_observation_digest=observation.observation_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={
                "semantic_observation": observation.to_dict(),
                "sanitized_content_references": [content_ref.to_dict()],
            },
        )
    )
    return observation, content_ref


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
    **kwargs: Any,
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
    defaults = {
        "coverage_state": CoverageState.SATISFIED,
        "semantic_support_status": SemanticSupportStatus.SUPPORTED,
        "source_obligation_status": SourceObligationStatus.NOT_APPLICABLE,
        "content_availability_status": ContentAvailabilityStatus.AVAILABLE,
        "evidence_custody_status": EvidenceCustodyStatus.CUSTODIED,
        "evidence_basis": (
            EvidenceBasis.SEMANTIC_OBSERVATION,
            EvidenceBasis.ANSWER_BEARING_CONTENT,
            EvidenceBasis.EVIDENCE_LEDGER_CUSTODY,
        ),
        "remaining_unknowns": (),
        "required_caveats": ("Currentness remains evidence-bound.",),
        "followup_need": FollowupNeed.NONE,
        "mode_budget_posture": ModeBudgetPosture.AVAILABLE,
        "conflict_posture": ConflictPosture.NONE,
        "currentness_posture": CurrentnessPosture.CURRENT,
        "stale": False,
    }
    defaults.update(kwargs)
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
        support_posture=SupportPosture.DIRECT,
        derived_support_status=DerivedSupportStatus.NOT_APPLICABLE,
        version_validity=VersionValidity.VALID,
        accepted_observation_refs=(obs_ref,),
        content_reference_bindings=(content_binding,),
        normalization_posture=ExplicitnessPosture.NOT_APPLICABLE,
        assumption_posture=ExplicitnessPosture.NOT_APPLICABLE,
        prohibited_upgrades=("Do not replace official value with estimate.",),
        metadata={"safe_note": "kept"},
        **defaults,
    )


def _reduce_coverage(kernel: RunKernel, accepted: dict[str, object], record: ComponentCoverageRecord) -> None:
    from core.run_kernel import Observation, ObservationType

    component_ref = accepted["accepted_answer_component_refs"][0]
    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    action = kernel.authorize_component_coverage_reduction(
        coverage_record_id=record.record_id,
        coverage_record_digest=record.record_digest,
        answer_component_id=component_ref["component_id"],
        component_revision=component_ref["component_revision"],
        component_digest=component_ref["component_digest"],
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.COMPONENT_COVERAGE_REDUCED,
            status=RunStageStatus.COMPLETED,
            payload={"component_coverage_record": payload},
        )
    )


def _amendment_record(
    accepted: dict[str, object],
    *,
    disposition: ProposalDisposition = ProposalDisposition.PROPOSED,
    materiality: MaterialityPosture = MaterialityPosture.NON_MATERIAL,
    user_confirmation_posture: UserConfirmationPosture = UserConfirmationPosture.NOT_REQUIRED,
    weakening_posture: WeakeningPosture = WeakeningPosture.NONE,
    coverage_candidates: tuple[CoverageInvalidationCandidateRef, ...] = (),
    rejection_reasons: tuple[str, ...] = (),
    blocking_reasons: tuple[str, ...] = (),
    candidate_new_contract_version: str | None = "0.2-candidate",
    candidate_new_contract_digest: str | None = "d" * 64,
) -> ContractAmendmentRecord:
    component_ref = accepted["accepted_answer_component_refs"][0]
    contract_version = str(accepted["accepted_contract_version"])
    return ContractAmendmentRecord(
        amendment_record_id=AMENDMENT_RECORD_ID,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-09",
        parent_contract_version=contract_version,
        parent_contract_digest=str(accepted["accepted_contract_digest"]),
        parent_question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        parent_question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        accepted_contract_ref=f"contract:{contract_version}:accepted",
        trigger_refs=AmendmentTriggerRefs(
            semantic_observation_refs=("observation:supports-reported-total",),
            evidence_refs=(EVIDENCE_ID,),
            sanitized_content_refs=("content:reported-total-value",),
            component_coverage_refs=(COVERAGE_RECORD_ID,),
            gap_refs=("gap:currentness",),
        ),
        affected_component_refs=(
            AffectedComponentRef(
                component_id=component_ref["component_id"],
                component_revision=component_ref["component_revision"],
                component_digest=component_ref["component_digest"],
            ),
        ),
        operations=(
            AmendmentOperation(
                operation_id="op:add-caveat",
                operation_kind=AmendmentOperationKind.ADD_CAVEAT,
                target_component_id=component_ref["component_id"],
                summary="Add caveat",
            ),
        ),
        materiality=materiality,
        user_confirmation_posture=user_confirmation_posture,
        monotonicity=MonotonicityPosture.PRESERVES,
        weakening_posture=weakening_posture,
        mode_permission_posture=ModePermissionPosture.WITHIN_MODE,
        disposition=disposition,
        candidate_invalidated_coverage_refs=coverage_candidates,
        stale_coverage_candidate_posture=StaleCoverageCandidatePosture.NOT_APPLICABLE,
        candidate_new_contract_version=candidate_new_contract_version,
        candidate_new_contract_digest=candidate_new_contract_digest,
        required_caveats=("Semantic caveat from amendment candidate.",),
        prohibited_upgrades=("Do not promote candidate amendment.",),
        rejection_reasons=rejection_reasons,
        blocking_reasons=blocking_reasons,
        metadata={"safe_note": "kept"},
    )


def _admit_amendment(kernel: RunKernel, record: ContractAmendmentRecord) -> None:
    from core.run_kernel import Observation, ObservationType

    payload = record.to_dict(include_validation=False)
    payload["record_digest"] = record.record_digest
    action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
    )
    kernel.reduce(
        Observation.from_action(
            action,
            observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
            status=RunStageStatus.COMPLETED,
            payload={"contract_amendment_record": payload},
        )
    )


def _accepted_contract(kernel: RunKernel) -> dict[str, Any]:
    return dict(kernel.state.initial_answer_contract)


def _coverage_history_entry(accepted: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    component_ref = accepted["accepted_answer_component_refs"][0]
    entry = {
        "answer_component_id": component_ref["component_id"],
        "accepted_contract_version": accepted["accepted_contract_version"],
        "accepted_contract_digest": accepted["accepted_contract_digest"],
        "component_revision": component_ref["component_revision"],
        "component_digest": component_ref["component_digest"],
        "coverage_record_id": COVERAGE_RECORD_ID,
        "coverage_state": "satisfied",
        "semantic_support_status": "supported",
        "source_obligation_status": "not_applicable",
        "content_availability_status": "available",
        "evidence_custody_status": "custodied",
        "evidence_basis": [
            "semantic_observation",
            "answer_bearing_content",
            "evidence_ledger_custody",
        ],
        "stale": False,
        "remaining_unknowns": [],
        "followup_need": "none",
        "conflict_posture": "none",
        "required_caveats": [],
        "prohibited_upgrades": [],
        "evidence_ledger_binding": {
            "ledger_snapshot_id": "fixture-ledger",
            "ledger_schema_version": EVIDENCE_LEDGER_SCHEMA_VERSION,
            "ledger_digest": "fixture-ledger-digest",
            "custody_status": "custodied",
            "source_requirement_ids": [],
            "ledger_observation_refs": [],
            "version_validity": "valid",
        },
        "content_reference_bindings": [
            {
                "content_ref_id": "content:reported-total-value",
                "content_digest": "fixture-content-digest",
                "evidence_ref_id": EVIDENCE_ID,
                "answer_component_id": component_ref["component_id"],
                "component_revision": component_ref["component_revision"],
                "component_contract_digest": component_ref["component_digest"],
                "answer_bearing": True,
                "availability_status": "available",
            }
        ],
    }
    entry.update(overrides)
    if isinstance(entry.get("remaining_unknowns"), tuple):
        entry["remaining_unknowns"] = list(entry["remaining_unknowns"])
    if isinstance(entry.get("evidence_basis"), tuple):
        entry["evidence_basis"] = [item.value if hasattr(item, "value") else item for item in entry["evidence_basis"]]
    for key in ("coverage_state", "followup_need", "conflict_posture"):
        value = entry.get(key)
        if hasattr(value, "value"):
            entry[key] = value.value
    for key in (
        "semantic_support_status",
        "source_obligation_status",
        "content_availability_status",
        "evidence_custody_status",
    ):
        value = entry.get(key)
        if hasattr(value, "value"):
            entry[key] = value.value
    return entry


def _amendment_history_entry(accepted: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    entry = {
        "amendment_record_id": AMENDMENT_RECORD_ID,
        "disposition": "proposed",
        "materiality": "non_material",
        "user_confirmation_posture": "not_required",
        "weakening_posture": "none",
        "blocking_reasons": [],
        "rejection_reasons": [],
        "candidate_invalidated_coverage_refs": [],
        "candidate_new_contract_version": None,
        "candidate_new_contract_digest": None,
        "required_caveats": [],
        "prohibited_upgrades": [],
    }
    entry.update(overrides)
    for key in ("disposition", "materiality", "user_confirmation_posture", "weakening_posture"):
        value = entry.get(key)
        if hasattr(value, "value"):
            entry[key] = value.value
    return entry


def _judgment_with_semantic(
    accepted: dict[str, Any],
    *,
    coverage_history: list[dict[str, Any]] | None = None,
    amendment_history: list[dict[str, Any]] | None = None,
    ledger: dict[str, Any] | None = None,
) -> Any:
    contract = _contract()
    ledger = ledger or _ledger_projection(contract)
    facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=accepted,
        component_coverage_history=coverage_history or [],
        contract_amendment_admission_history=amendment_history or [],
        evidence_ledger_projection=ledger,
    )
    return build_deterministic_sufficiency_judgment(
        _input(contract, ledger, semantic_state_facts=facts)
    )


def _kernel_with_semantic(
    *,
    coverage_kwargs: dict[str, Any] | None = None,
    include_coverage: bool = True,
    amendment_record: ContractAmendmentRecord | None = None,
) -> RunKernel:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    _seed_evidence_ledger(kernel)
    observation, content_ref = _admit(kernel, accepted)
    if include_coverage:
        record = _coverage_record(
            accepted,
            observation,
            content_ref,
            kernel,
            **(coverage_kwargs or {}),
        )
        _reduce_coverage(kernel, accepted, record)
    if amendment_record is not None:
        _admit_amendment(kernel, amendment_record)
    return kernel


def _input(
    contract: dict[str, Any],
    ledger: dict[str, Any],
    kernel: RunKernel | None = None,
    *,
    semantic_state_facts: dict[str, Any] | None = None,
) -> RunSufficiencyJudgmentInput:
    facts = semantic_state_facts
    if facts is None and kernel is not None:
        facts = build_semantic_state_facts_for_sufficiency(
            initial_answer_contract=kernel.state.initial_answer_contract,
            component_coverage_history=kernel.state.component_coverage_history,
            contract_amendment_admission_history=kernel.state.contract_amendment_admission_history,
            evidence_ledger_projection=ledger,
        )
    return RunSufficiencyJudgmentInput(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        search_judgment_projection={"decision": "stop_satisfied"},
        final_evidence_facts={"final_evidence_count": 1, "author_evidence_count": 1},
        semantic_state_facts=facts or {},
    )


def _judgment(kernel: RunKernel | None, *, contract: dict[str, Any] | None = None) -> Any:
    contract = contract or _contract()
    ledger = _ledger_projection(contract, satisfied=True)
    return build_deterministic_sufficiency_judgment(_input(contract, ledger, kernel))


def _adapter_input_for_kernel(
    kernel: RunKernel,
    *,
    ledger: dict[str, Any] | None = None,
) -> RunSufficiencyJudgmentInput:
    contract = _contract()
    ledger = ledger or _ledger_projection(contract)
    return build_sufficiency_judgment_input_from_runtime(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        search_judgment_projection={"decision": "stop_satisfied"},
        search_judgment_history=[],
        answer_contract_projection={},
        final_evidence_count=1,
        author_evidence_count=1,
        citation_eligible_candidate_count=1,
        conflicts_present=False,
        scrutineer_flag_count=0,
        corpus_weak=False,
        weak_corpus_reason=None,
        synth_was_insufficient=False,
        failure_card_show=False,
        failure_card_reason=None,
        iterations_run=1,
        max_iterations=3,
        recovery_attempt_count=0,
        initial_answer_contract=kernel.state.initial_answer_contract,
        component_coverage_history=kernel.state.component_coverage_history,
        contract_amendment_admission_history=kernel.state.contract_amendment_admission_history,
    )


def _adapter_judgment_for_kernel(
    kernel: RunKernel,
    *,
    ledger: dict[str, Any] | None = None,
) -> Any:
    return build_deterministic_sufficiency_judgment(
        _adapter_input_for_kernel(kernel, ledger=ledger)
    )


def test_semantic_facts_in_input_and_projection_exclude_sensitive_data() -> None:
    kernel = _kernel_with_semantic()
    contract = _contract()
    ledger = _ledger_projection(contract)
    judgment_input = build_sufficiency_judgment_input_from_runtime(
        contract_projection=contract,
        evidence_ledger_projection=ledger,
        search_judgment_projection={"decision": "stop_satisfied"},
        search_judgment_history=[],
        answer_contract_projection={},
        final_evidence_count=1,
        author_evidence_count=1,
        citation_eligible_candidate_count=1,
        conflicts_present=False,
        scrutineer_flag_count=0,
        corpus_weak=False,
        weak_corpus_reason=None,
        synth_was_insufficient=False,
        failure_card_show=False,
        failure_card_reason=None,
        iterations_run=1,
        max_iterations=3,
        recovery_attempt_count=0,
        initial_answer_contract=kernel.state.initial_answer_contract,
        component_coverage_history=kernel.state.component_coverage_history,
        contract_amendment_admission_history=kernel.state.contract_amendment_admission_history,
    )
    projection = _judgment(kernel).to_projection()
    serialized = json.dumps(
        {
            "input": judgment_input.to_model_payload(),
            "projection": projection,
        },
        sort_keys=True,
    ).casefold()

    assert judgment_input.semantic_state_facts["schema_version"] == (
        SUFFICIENCY_SEMANTIC_STATE_CONSUMPTION_SCHEMA_VERSION
    )
    assert projection["semantic_consumption"]["blocker_count"] == 0
    assert projection["semantic_state_facts_summary"]["semantic_state_facts_digest"]
    for forbidden in ("raw_prompt", "private_sentinel", "full_trace"):
        assert forbidden not in serialized
    assert '"provider_payload_retained": false' in serialized


def test_all_required_components_satisfied_preserves_ready_direct() -> None:
    kernel = _kernel_with_semantic()
    judgment = _judgment(kernel)
    assert judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert judgment.final_answer_allowed is True
    assert not judgment.semantic_consumption.get("direct_answer_blocked")


def test_missing_required_component_emits_version_bound_gap_identity() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    component_ref = accepted["accepted_answer_component_refs"][0]

    facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=accepted,
        component_coverage_history=[],
        contract_amendment_admission_history=[],
        evidence_ledger_projection=_ledger_projection(_contract()),
    )
    missing = facts["blockers"][0]
    overlay = evaluate_semantic_sufficiency_overlay(facts)
    assessment = overlay.missing_assessments[0]

    assert missing["code"] == "missing_required_component_coverage"
    assert missing["accepted_contract_version"] == accepted["accepted_contract_version"]
    assert missing["accepted_contract_digest"] == accepted["accepted_contract_digest"]
    assert missing["ref_id"] == component_ref["component_id"]
    assert missing["component_digest"] == component_ref["component_digest"]
    assert facts["accepted_required_component_refs"] == [
        {
            "answer_component_id": component_ref["component_id"],
            "component_digest": component_ref["component_digest"],
            "accepted_contract_version": accepted["accepted_contract_version"],
            "accepted_contract_digest": accepted["accepted_contract_digest"],
        }
    ]
    assert assessment["accepted_contract_version"] == accepted[
        "accepted_contract_version"
    ]
    assert assessment["accepted_contract_digest"] == accepted[
        "accepted_contract_digest"
    ]
    assert assessment["answer_component_id"] == component_ref["component_id"]
    assert assessment["component_digest"] == component_ref["component_digest"]
    assert assessment["semantic_gap_code"] == "missing_required_component_coverage"


def test_stale_contract_bound_coverage_is_ignored_as_orphan_state() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    stale_coverage = _coverage_history_entry(
        accepted,
        accepted_contract_digest="stale-contract-digest",
    )

    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[stale_coverage],
    )
    semantic_consumption = judgment.semantic_consumption
    assert "stale_or_orphan_component_coverage" in semantic_consumption[
        "blocker_codes"
    ]
    assert "missing_required_component_coverage" in semantic_consumption[
        "blocker_codes"
    ]
    assert semantic_consumption["direct_answer_blocked"] is True
    assert semantic_consumption["covered_component_count"] == 0
    assert semantic_consumption["missing_component_count"] == 1
    assert semantic_consumption["semantic_ref_projection"]["available"] is False
    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT


def test_ready_direct_is_repaired_when_coverage_has_only_unqualified_ledger_presence() -> None:
    from core.run_authority_sufficiency_validation import validate_or_repair_sufficiency_judgment

    kernel = _kernel_with_semantic()
    ledger = _ledger_projection(_contract(), semantic_candidate_disposition="observed")
    deterministic = _adapter_judgment_for_kernel(kernel, ledger=ledger)
    unsafe = {
        "decision": RunSufficiencyDecision.READY_DIRECT.value,
        "final_answer_posture": SufficiencyPosture.DIRECT_ANSWER.value,
        "contract_fulfilled": True,
        "required_obligations_satisfied": True,
        "final_answer_allowed": True,
    }

    repaired, validation = validate_or_repair_sufficiency_judgment(
        unsafe,
        deterministic_judgment=deterministic,
        model_attempted=True,
    )

    assert "ledger_candidate_not_qualified" in deterministic.semantic_consumption["blocker_codes"]
    assert deterministic.semantic_consumption["direct_answer_blocked"] is True
    assert validation.status.value == "repaired"
    assert repaired.final_answer_allowed is False
    assert repaired.decision is not RunSufficiencyDecision.READY_DIRECT


def test_ready_direct_is_blocked_when_current_relevant_ledger_facts_weaken() -> None:
    kernel = _kernel_with_semantic()
    weakened_ledger = _ledger_projection(
        _contract(),
        semantic_candidate_disposition="rejected",
    )

    judgment = _adapter_judgment_for_kernel(kernel, ledger=weakened_ledger)

    assert "ledger_candidate_rejected_or_unavailable" in judgment.semantic_consumption["blocker_codes"]
    assert judgment.semantic_consumption["direct_answer_blocked"] is True
    assert judgment.final_answer_allowed is False
    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT


def test_unrelated_evidence_ledger_additions_do_not_block_satisfied_coverage() -> None:
    kernel = _kernel_with_semantic()
    ledger = _ledger_projection(_contract())
    ledger["candidate_records"].append(
        {
            "candidate_id": "evidence:unrelated-rejected",
            "fact_disposition": "rejected",
            "readable_status": "unreadable",
            "fetchable_status": "unfetchable",
        }
    )
    ledger["custody_records"].append(
        {
            "candidate_id": "evidence:unrelated-rejected",
            "record_kind": "fact",
            "disposition": "rejected",
        }
    )
    ledger["candidate_count"] = int(ledger.get("candidate_count") or 0) + 1
    ledger["custody_record_count"] = int(ledger.get("custody_record_count") or 0) + 1

    judgment = _adapter_judgment_for_kernel(kernel, ledger=ledger)

    assert judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert judgment.final_answer_allowed is True
    assert not judgment.semantic_consumption.get("direct_answer_blocked")


@pytest.mark.parametrize(
    ("ledger_mutation", "expected_code"),
    [
        ("missing_candidate", "ledger_candidate_missing"),
        ("missing_custody", "ledger_candidate_custody_fact_missing"),
        ("missing_requirement", "ledger_source_requirement_missing"),
    ],
)
def test_missing_relevant_candidate_custody_or_requirement_facts_block(
    ledger_mutation: str,
    expected_code: str,
) -> None:
    kernel = _kernel_with_semantic()
    ledger = _ledger_projection(_contract())
    normalized_evidence_id = EVIDENCE_ID.replace("-", "_")
    if ledger_mutation == "missing_candidate":
        ledger["candidate_records"] = [
            item
            for item in ledger["candidate_records"]
            if item.get("candidate_id") != normalized_evidence_id
        ]
    elif ledger_mutation == "missing_custody":
        ledger["custody_records"] = [
            item
            for item in ledger["custody_records"]
            if item.get("candidate_id") != normalized_evidence_id
        ]
    else:
        coverage = dict(kernel.state.component_coverage_history[-1])
        binding = dict(coverage["evidence_ledger_binding"])
        binding["source_requirement_ids"] = ["source_requirement:official_current_rules"]
        coverage["evidence_ledger_binding"] = binding
        coverage["source_obligation_status"] = "satisfied"
        kernel.state.component_coverage_history[-1] = coverage

    judgment = _adapter_judgment_for_kernel(kernel, ledger=ledger)

    assert expected_code in judgment.semantic_consumption["blocker_codes"]
    assert judgment.semantic_consumption["direct_answer_blocked"] is True
    assert judgment.final_answer_allowed is False


def test_semantic_state_facts_record_bounded_ledger_blocker_without_raw_retention() -> None:
    kernel = _kernel_with_semantic()
    coverage = dict(kernel.state.component_coverage_history[-1])
    coverage["raw_content"] = "SENTINEL_RAW_CONTENT"
    kernel.state.component_coverage_history[-1] = coverage
    ledger = _ledger_projection(_contract(), semantic_candidate_disposition="observed")
    judgment_input = _adapter_input_for_kernel(kernel, ledger=ledger)
    serialized = json.dumps(judgment_input.semantic_state_facts, sort_keys=True)

    assert "ledger_candidate_not_qualified" in serialized
    assert "coverage-bound evidence is only observed" in serialized
    assert "SENTINEL_RAW_CONTENT" not in serialized


@pytest.mark.parametrize(
    ("coverage_overrides", "expected_code", "attr"),
    [
        ({}, "missing_required_component_coverage", "direct_answer_blocked"),
        ({"coverage_state": "partial"}, "partial_or_unsupported_coverage", "direct_answer_blocked"),
        ({"coverage_state": "unsupported"}, "partial_or_unsupported_coverage", "direct_answer_blocked"),
        ({"stale": True, "coverage_state": "stale"}, "stale_coverage", "finalization_blocked"),
        ({"coverage_state": "conflicted", "conflict_posture": "present"}, "conflicted_coverage", "finalization_blocked"),
        ({"remaining_unknowns": ["unit basis"]}, "remaining_unknowns", "direct_answer_blocked"),
        ({"followup_need": "required"}, "followup_need_required_or_blocked", "finalization_blocked"),
        ({"source_obligation_status": "unsatisfied"}, "source_obligation_unsatisfied", "direct_answer_blocked"),
        ({"content_availability_status": "missing"}, "content_unavailable", "direct_answer_blocked"),
        ({"evidence_custody_status": "unknown"}, "evidence_not_custodied", "direct_answer_blocked"),
        (
            {"evidence_basis": ["candidate_discovery", "search_result_snippet"]},
            "weak_only_evidence_basis",
            "direct_answer_blocked",
        ),
    ],
)
def test_semantic_blockers(
    coverage_overrides: dict[str, Any],
    expected_code: str,
    attr: str,
) -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    if coverage_overrides:
        history = [_coverage_history_entry(accepted, **coverage_overrides)]
    else:
        history = []
    judgment = _judgment_with_semantic(accepted, coverage_history=history)
    assert expected_code in judgment.semantic_consumption.get("blocker_codes", [])
    assert judgment.semantic_consumption[attr] is True
    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT


def test_semantic_caveats_and_prohibited_upgrades_merge_into_projection() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[
            _coverage_history_entry(
                accepted,
                required_caveats=["Keep caveat A."],
                prohibited_upgrades=["No upgrade A."],
            )
        ],
    )
    assert "Keep caveat A." in judgment.mandatory_caveats
    assert "No upgrade A." in judgment.prohibited_upgrades
    assert "Keep caveat A." in judgment.to_projection()["mandatory_caveats"]


def test_material_amendment_requiring_confirmation_blocks_finalization() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[_coverage_history_entry(accepted)],
        amendment_history=[
            _amendment_history_entry(
                accepted,
                materiality="material",
                disposition="requires_user_confirmation",
                user_confirmation_posture="requires_user_confirmation",
            )
        ],
    )
    assert judgment.decision is RunSufficiencyDecision.BLOCK_FINALIZATION
    assert judgment.semantic_consumption["finalization_blocked"] is True


def test_blocked_amendment_candidate_blocks_finalization() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[_coverage_history_entry(accepted)],
        amendment_history=[
            _amendment_history_entry(
                accepted,
                disposition="blocked",
                blocking_reasons=["policy_blocked"],
            )
        ],
    )
    assert judgment.decision is RunSufficiencyDecision.BLOCK_FINALIZATION


def test_rejected_amendment_with_ordinary_reasons_does_not_block() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[_coverage_history_entry(accepted)],
        amendment_history=[
            _amendment_history_entry(
                accepted,
                disposition="rejected",
                rejection_reasons=["ordinary_non_material_rejection"],
            )
        ],
    )
    assert judgment.decision is RunSufficiencyDecision.READY_DIRECT
    assert "amendment_blocked" not in judgment.semantic_consumption.get("blocker_codes", [])


def test_weakening_without_user_authority_blocks_finalization() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[_coverage_history_entry(accepted)],
        amendment_history=[
            _amendment_history_entry(
                accepted,
                weakening_posture="removes_requirement",
                user_confirmation_posture="not_required",
            )
        ],
    )
    assert judgment.decision is RunSufficiencyDecision.BLOCK_FINALIZATION
    assert "amendment_weakening_without_authority" in judgment.semantic_consumption["blocker_codes"]


def test_candidate_invalidated_coverage_ref_makes_linked_coverage_suspect_without_mutation() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    coverage_history = [_coverage_history_entry(accepted)]
    amendment_history = [
        _amendment_history_entry(
            accepted,
            candidate_invalidated_coverage_refs=[
                {
                    "coverage_record_id": COVERAGE_RECORD_ID,
                    "answer_component_id": COMPONENT_ID,
                    "represented_only": True,
                }
            ],
        )
    ]
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=coverage_history,
        amendment_history=amendment_history,
    )
    assert COMPONENT_ID in judgment.semantic_consumption["coverage_suspect_component_ids"]
    assert judgment.decision is not RunSufficiencyDecision.READY_DIRECT


def test_candidate_new_contract_version_remains_candidate_only() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    before_digest = accepted["accepted_contract_digest"]
    judgment = _judgment_with_semantic(
        accepted,
        coverage_history=[_coverage_history_entry(accepted)],
        amendment_history=[
            _amendment_history_entry(
                accepted,
                candidate_new_contract_version="9.9-candidate-only",
                candidate_new_contract_digest="c" * 64,
            )
        ],
    )
    assert kernel.state.initial_answer_contract["accepted_contract_digest"] == before_digest
    assert "9.9-candidate-only" in judgment.semantic_consumption["candidate_new_contract_versions"]


def test_model_ready_direct_over_semantic_blockers_is_repaired() -> None:
    from core.run_authority_sufficiency_validation import validate_or_repair_sufficiency_judgment

    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    contract = _contract()
    ledger = _ledger_projection(contract)
    facts = build_semantic_state_facts_for_sufficiency(
        initial_answer_contract=accepted,
        component_coverage_history=[],
        contract_amendment_admission_history=[],
        evidence_ledger_projection=ledger,
    )
    deterministic = build_deterministic_sufficiency_judgment(
        _input(contract, ledger, semantic_state_facts=facts)
    )
    unsafe = {
        "decision": RunSufficiencyDecision.READY_DIRECT.value,
        "final_answer_posture": SufficiencyPosture.DIRECT_ANSWER.value,
        "contract_fulfilled": True,
        "required_obligations_satisfied": True,
        "final_answer_allowed": True,
    }
    repaired, validation = validate_or_repair_sufficiency_judgment(
        unsafe,
        deterministic_judgment=deterministic,
        model_attempted=True,
    )
    assert validation.status.value == "repaired"
    assert repaired.decision is not RunSufficiencyDecision.READY_DIRECT
    assert repaired.final_answer_allowed is False


def test_model_block_finalization_with_answer_allowed_true_is_repaired() -> None:
    from core.run_authority_sufficiency_validation import validate_or_repair_sufficiency_judgment

    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    accepted = _accept_contract(kernel)
    deterministic = _judgment_with_semantic(
        accepted,
        coverage_history=[
            _coverage_history_entry(
                accepted,
                stale=True,
                coverage_state="stale",
            )
        ],
    )
    model_payload = dict(deterministic.to_projection())
    model_payload["final_answer_allowed"] = True

    repaired, validation = validate_or_repair_sufficiency_judgment(
        model_payload,
        deterministic_judgment=deterministic,
        model_attempted=True,
    )

    assert validation.status.value == "repaired"
    assert repaired.final_answer_allowed is False
    assert "restored_semantic_finalization_answer_allowed_false" in validation.reasons
    assert repaired.semantic_consumption["finalization_blocked"] is True


def test_projection_digest_is_deterministic() -> None:
    kernel = _kernel_with_semantic()
    one = _judgment(kernel).to_projection()["semantic_state_facts_summary"]["semantic_state_facts_digest"]
    two = _judgment(kernel).to_projection()["semantic_state_facts_summary"]["semantic_state_facts_digest"]
    assert one == two


def test_static_guards_no_pipeline_orchestrator_or_forbidden_imports() -> None:
    source = RUNTIME_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        (node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "core.pipeline_orchestrator" not in imports
    assert "core.run_kernel" not in imports
    assert "sufficiency_semantic_consume" not in RUN_KERNEL.read_text(encoding="utf-8")
    assert "semantic_consumption_history" not in RUN_KERNEL.read_text(encoding="utf-8")
    assert "ledger_qualification_history" not in RUN_KERNEL.read_text(encoding="utf-8")
    assert "semantic_ledger_bridge" not in RUN_KERNEL.read_text(encoding="utf-8")
    assert "build_deterministic_sufficiency_judgment" not in PIPELINE.read_text(encoding="utf-8")
