from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from core.contract_amendment_application_runtime import (
    CONTRACT_AMENDMENT_APPLICATION_SCHEMA_VERSION,
    CONTRACT_AMENDMENT_APPLICATION_STAGE,
    CURRENT_ANSWER_CONTRACT_SCHEMA_VERSION,
    REQUIREMENT_LIFECYCLE_STATUSES,
    ContractAmendmentApplicationError,
    build_contract_amendment_application_state,
)
from core.contract_amendment_record import (
    AffectedComponentRef,
    AmendmentOperation,
    AmendmentOperationKind,
    MaterialityPosture,
    ProposalDisposition,
    StaleCoverageCandidatePosture,
    UserConfirmationPosture,
)
from core.run_authority_sufficiency_adapter import (
    build_sufficiency_judgment_input_from_runtime,
)
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
    RequirementPosture,
    SupportKind,
)
from tests.test_ag_sem_08_contract_amendment_admission import (
    COMPONENT_ID,
    RUN_ID,
    _admit_amendment,
    _amendment_record,
    _coverage_candidate,
    _start_admitted_kernel_with_coverage,
)

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_RUNTIME = ROOT / "core" / "contract_amendment_application_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
SUFFICIENCY_CONSUMPTION = (
    ROOT / "core" / "sufficiency_semantic_state_consumption_runtime.py"
)

NEW_COMPONENT_ID = "component:confidence-band"


def _new_component() -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id=NEW_COMPONENT_ID,
        component_revision="1",
        user_facing_label="Confidence band",
        user_facing_question="What caveat bounds the reported total?",
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=(
            "state that the total is evidence-bound",
            "do not upgrade the total beyond the cited record",
        ),
        semantic_slot_ids=("slot:reporting-period",),
        source_obligation_candidate_ids=(
            "source-obligation:confidence-band",
        ),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        materiality=Materiality.MATERIAL,
    )


def _add_component_record(
    kernel: RunKernel,
    accepted: dict[str, Any],
    *,
    disposition: ProposalDisposition = (
        ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE
    ),
):
    component = _new_component().to_dict()
    operation = AmendmentOperation(
        operation_id="operation:add-confidence-band",
        operation_kind=AmendmentOperationKind.ADD_COMPONENT,
        operation_payload={"component": component},
    )
    affected = AffectedComponentRef(
        component_id=component["component_id"],
        component_revision=component["component_revision"],
        component_digest=component["component_digest"],
        relationship="new_component",
    )
    return _amendment_record(
        accepted,
        disposition=disposition,
        operations=(operation,),
        affected_component_refs=(affected,),
        coverage_candidates=(_coverage_candidate(kernel),),
        stale_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )


def _admit_add_component() -> tuple[RunKernel, dict[str, Any], Any]:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    record = _add_component_record(kernel, accepted)
    _admit_amendment(kernel, accepted, record)
    return kernel, accepted, record


def _apply_admitted(kernel: RunKernel, record: Any) -> dict[str, Any]:
    admission = kernel.state.contract_amendment_admission_projection
    action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=admission["admission_digest"],
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
        status=RunStageStatus.COMPLETED,
        payload={},
    )
    kernel.reduce(observation)
    return kernel.state.contract_amendment_application_state


def _serialized(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def test_application_creates_current_answer_contract_version() -> None:
    kernel, accepted, record = _admit_add_component()

    application_state = _apply_admitted(kernel, record)

    current = kernel.state.current_answer_contract
    assert application_state["schema_version"] == CONTRACT_AMENDMENT_APPLICATION_SCHEMA_VERSION
    assert current["schema_version"] == CURRENT_ANSWER_CONTRACT_SCHEMA_VERSION
    assert current["accepted_contract_version"] != accepted["accepted_contract_version"]
    assert current["accepted_contract_digest"] != accepted["accepted_contract_digest"]
    assert current["previous_contract_digest"] == accepted["accepted_contract_digest"]
    assert current["initial_contract_digest"] == accepted["accepted_contract_digest"]
    assert NEW_COMPONENT_ID in {
        item["component_id"] for item in current["accepted_answer_component_refs"]
    }
    assert application_state["application_digest"]
    assert application_state["lineage"]["created_by"] == "RunKernel.ContractAmendmentApplication"
    assert current["lineage"]["application_digest"] == application_state["application_digest"]
    assert kernel.state.stage_statuses[CONTRACT_AMENDMENT_APPLICATION_STAGE] is RunStageStatus.COMPLETED


def test_amendment_admission_remains_non_mutating() -> None:
    kernel, accepted, record = _admit_add_component()
    admitted_before = dict(kernel.state.contract_amendment_admission_projection)
    initial_digest = kernel.state.initial_answer_contract["accepted_contract_digest"]

    _apply_admitted(kernel, record)

    admitted_after = kernel.state.contract_amendment_admission_history[-1]
    assert admitted_after == admitted_before
    assert admitted_after["contract_mutation_applied"] is False
    assert admitted_after["amendment_applied"] is False
    assert kernel.state.initial_answer_contract["accepted_contract_digest"] == initial_digest
    assert kernel.state.initial_answer_contract == accepted


def test_application_rejects_stale_parent_contract_digest() -> None:
    kernel, _accepted, record = _admit_add_component()
    admission = kernel.state.contract_amendment_admission_projection
    action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=admission["admission_digest"],
        parent_contract_digest="0" * 64,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
        status=RunStageStatus.COMPLETED,
        payload={},
    )

    with pytest.raises(RunKernelTransitionError, match="stale parent contract digest"):
        kernel.reduce(observation)


def test_exact_application_replay_precedes_currentness_and_is_mutation_free() -> None:
    kernel, _accepted, record = _admit_add_component()
    _apply_admitted(kernel, record)

    admission = kernel.state.contract_amendment_admission_projection
    application_before = list(
        kernel.state.contract_amendment_application_history
    )
    current_before = dict(kernel.state.current_answer_contract)
    observation_count = len(kernel.state.observations)

    replay = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=admission["admission_digest"],
    )

    assert replay["status"] == "exact_replay"
    assert replay["work_authorized"] is False
    assert replay["contract_amendment_application"] == application_before[0]
    assert (
        replay["new_contract_ref"]["accepted_contract_digest"]
        == current_before["accepted_contract_digest"]
    )
    assert (
        kernel.state.contract_amendment_application_history
        == application_before
    )
    assert kernel.state.current_answer_contract == current_before
    assert len(kernel.state.observations) == observation_count


def test_application_rejects_merely_proposed_admission_without_explicit_authority() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    initial_before = json.loads(json.dumps(kernel.state.initial_answer_contract))
    record = _add_component_record(
        kernel,
        accepted,
        disposition=ProposalDisposition.PROPOSED,
    )
    _admit_amendment(kernel, accepted, record)

    with pytest.raises(RunKernelTransitionError, match="requires eligible"):
        _apply_admitted(kernel, record)

    assert kernel.state.current_answer_contract == {}
    assert kernel.state.current_answer_contract_history == []
    assert kernel.state.initial_answer_contract == initial_before


def test_application_rejects_rejected_blocked_or_unconfirmed_material_admission() -> None:
    for disposition, expected in (
        (ProposalDisposition.REJECTED, "rejected"),
        (ProposalDisposition.BLOCKED, "blocked"),
    ):
        kernel, accepted, _record = _start_admitted_kernel_with_coverage()
        record = _amendment_record(accepted, disposition=disposition)
        _admit_amendment(kernel, accepted, record)
        with pytest.raises(RunKernelTransitionError, match=expected):
            _apply_admitted(kernel, record)

    kernel, accepted, record = _start_admitted_kernel_with_coverage()
    material = replace(
        record,
        disposition=ProposalDisposition.REQUIRES_USER_CONFIRMATION,
        materiality=MaterialityPosture.MATERIAL,
        user_confirmation_posture=UserConfirmationPosture.REQUIRES_USER_CONFIRMATION,
        candidate_invalidated_coverage_refs=(_coverage_candidate(kernel),),
        stale_coverage_candidate_posture=StaleCoverageCandidatePosture.CANDIDATE_STALE,
    )
    _admit_amendment(kernel, accepted, material)
    with pytest.raises(RunKernelTransitionError, match="requires explicit user"):
        _apply_admitted(kernel, material)


def test_current_contract_has_requirement_lifecycle_statuses() -> None:
    kernel, _accepted, record = _admit_add_component()

    _apply_admitted(kernel, record)

    current = kernel.state.current_answer_contract
    assert tuple(current["requirement_lifecycle_statuses"]) == REQUIREMENT_LIFECYCLE_STATUSES
    lifecycle = current["requirement_lifecycle"]
    assert lifecycle["status_definitions"]["satisfied"].startswith("the requirement is covered")
    assert {
        item["status"] for item in lifecycle["component_statuses"]
    } == {"pending"}
    assert {item["component_id"] for item in lifecycle["component_statuses"]} == {
        COMPONENT_ID,
        NEW_COMPONENT_ID,
    }


def test_satisfied_status_requires_semantic_coverage_and_ledger_qualification() -> None:
    kernel, accepted, _record = _start_admitted_kernel_with_coverage()
    operation = AmendmentOperation(
        operation_id="operation:mark-reported-total-satisfied",
        operation_kind=AmendmentOperationKind.ADD_CAVEAT,
        operation_payload={
            "normalized_operation_kind": "mark_requirement_satisfied",
            "component_id": COMPONENT_ID,
            "reason": "attempted status shortcut",
        },
    )
    record = _amendment_record(
        accepted,
        disposition=ProposalDisposition.ELIGIBLE_FOR_FUTURE_ACCEPTANCE,
        operations=(operation,),
    )
    _admit_amendment(kernel, accepted, record)
    admission = kernel.state.contract_amendment_admission_projection
    action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record.amendment_record_id,
        amendment_record_digest=record.record_digest,
        admission_digest=admission["admission_digest"],
    )

    with pytest.raises(
        ContractAmendmentApplicationError,
        match="satisfied status requires matching semantic coverage",
    ):
        build_contract_amendment_application_state(
            action_id=action.action_id,
            action_inputs=action.inputs,
            admitted_amendment=admission,
            parent_contract=kernel.state.initial_answer_contract,
            initial_contract=kernel.state.initial_answer_contract,
            component_coverage_history=(),
            evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
            application_history=(),
            run_id=RUN_ID,
            request_id=kernel.state.request_id,
        )


def test_sufficiency_consumes_current_answer_contract_not_only_initial() -> None:
    kernel, accepted, record = _admit_add_component()
    _apply_admitted(kernel, record)

    judgment_input = build_sufficiency_judgment_input_from_runtime(
        contract_projection={},
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        search_judgment_projection={},
        search_judgment_history=(),
        answer_contract_projection={},
        final_evidence_count=0,
        author_evidence_count=0,
        citation_eligible_candidate_count=0,
        conflicts_present=False,
        scrutineer_flag_count=0,
        corpus_weak=False,
        weak_corpus_reason=None,
        synth_was_insufficient=False,
        failure_card_show=False,
        failure_card_reason=None,
        iterations_run=0,
        max_iterations=3,
        recovery_attempt_count=0,
        initial_answer_contract=kernel.state.initial_answer_contract,
        current_answer_contract=kernel.state.current_answer_contract,
        component_coverage_history=kernel.state.component_coverage_history,
        contract_amendment_admission_history=kernel.state.contract_amendment_admission_history,
    )
    facts = judgment_input.semantic_state_facts

    assert facts["current_answer_contract_consumed"] is True
    assert facts["accepted_contract_source"] == "current_answer_contract"
    assert facts["accepted_contract_digest"] == kernel.state.current_answer_contract["accepted_contract_digest"]
    assert facts["accepted_contract_digest"] != accepted["accepted_contract_digest"]
    assert facts["required_component_count"] == 2
    assert any(
        blocker["code"] == "missing_required_component_coverage"
        and blocker["ref_id"] == NEW_COMPONENT_ID
        for blocker in facts["blockers"]
    )
    assert facts["direct_answer_blocked"] is True


def test_application_projection_excludes_raw_private_sentinels() -> None:
    kernel, _accepted, record = _admit_add_component()

    _apply_admitted(kernel, record)

    serialized = _serialized(kernel.state.contract_amendment_application_projection)
    assert "SENTINEL_RAW_PROMPT" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_provider_payload" not in serialized
    assert "provider_payload" not in serialized


def test_static_closed_surface_guard() -> None:
    runtime_text = APPLICATION_RUNTIME.read_text(encoding="utf-8")
    kernel_text = RUN_KERNEL.read_text(encoding="utf-8")
    sufficiency_text = SUFFICIENCY_CONSUMPTION.read_text(encoding="utf-8")

    assert "from core.run_kernel" not in runtime_text
    assert "import core.run_kernel" not in runtime_text
    for forbidden in ("requests.", "httpx.", "openai.", "Planner(", "Scout(", "SearchExecutor("):
        assert forbidden not in runtime_text
    assert "CONTRACT_AMENDMENT_APPLY" in kernel_text
    assert "CONTRACT_AMENDMENT_APPLIED" in kernel_text
    assert "current_answer_contract" in sufficiency_text


def test_docs_use_merge_stable_mutation_loop_posture() -> None:
    docs = {
        "loop": ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
        "guidance": ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
        "guide": ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
        "state": ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    }
    text = "\n".join(path.read_text(encoding="utf-8") for path in docs.values())

    assert "AG-RUN-CONTRACT-MUTATION-LOOP-01" in text
    assert "current_answer_contract" in text
    assert "AG-SEARCH-PLANNER-RUNTIME-01" in text
    assert "post-merge next gate is AG-RUN-CONTRACT-MUTATION-LOOP-01" not in text
    assert "live validation is next" not in text
    assert "partial-answer readiness is next" not in text
