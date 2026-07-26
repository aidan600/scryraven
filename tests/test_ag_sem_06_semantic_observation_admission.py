from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path

import pytest

from core.run_kernel import (
    SEMANTIC_OBSERVATION_ADMISSION_STAGE,
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
from core.semantic_observation_admission_runtime import (
    SEMANTIC_OBSERVATION_ADMISSION_SCHEMA_VERSION,
    SemanticObservationAdmissionError,
    build_semantic_observation_admission_projection,
    build_semantic_observation_admission_state,
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
RUNTIME_MODULE = ROOT / "core" / "semantic_observation_admission_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

RUN_ID = "run:sem-06-offline"
REQUEST_ID = "request:sem-06"

# Neutral fixture: a passive observation over a public-record "reported total".
# Deliberately not an aircraft example; nothing here is doctrine.
COMPONENT_ID = "component:reported-total"
EVIDENCE_ID = "evidence:public-record-notice"
SOURCE_OBLIGATION_ID = "obligation:reported-total-primary-source"


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
        source_obligation_candidate_ids=(SOURCE_OBLIGATION_ID,),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        materiality=Materiality.MATERIAL,
    )


def _qmr() -> QuestionMeaningRecord:
    return QuestionMeaningRecord(
        record_id="qmr:reported-total",
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-06",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-06-test",
        intent="Answer the reported-total question.",
        requested_output="Concise answer with primary-source support.",
        semantic_slots=(_slot(),),
        answer_components=(_component(),),
        metadata={"safe_note": "kept"},
    ).require_valid()


def _start_accepted_kernel() -> tuple[RunKernel, dict[str, object]]:
    """Start a kernel and accept an AG-SEM-05 initial answer contract."""

    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
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
    return kernel, kernel.state.initial_answer_contract


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


def _content_ref(
    accepted: dict[str, object],
    *,
    content_ref_id: str = "content:reported-total-value",
    evidence_ref_id: str = EVIDENCE_ID,
    bounded_text: str = "The 2026 reported total is 1,284 records.",
    component_revision: str | None = None,
    component_contract_digest: str | None = None,
    answer_component_id: str | None = None,
) -> SanitizedContentReference:
    component_ref = accepted["accepted_answer_component_refs"][0]
    return SanitizedContentReference(
        content_ref_id=content_ref_id,
        evidence_ref_id=evidence_ref_id,
        admitted_evidence_ref=evidence_ref_id,
        source_id="source:public-record",
        source_digest="source-digest-sem-06",
        source_url="https://example.org/public-record-notice",
        source_title="Public record notice",
        source_domain="example.org",
        answer_component_id=answer_component_id or component_ref["component_id"],
        component_revision=component_revision or component_ref["component_revision"],
        component_contract_digest=component_contract_digest or component_ref["component_digest"],
        question_meaning_record_id=accepted["parent_question_meaning_record_id"],
        question_meaning_record_digest=accepted["parent_question_meaning_record_digest"],
        content_kind=ContentKind.BOUNDED_EXCERPT,
        bounded_text=bounded_text,
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


def _observation(
    accepted: dict[str, object],
    *,
    observation_id: str = "observation:supports-reported-total",
    content_refs: tuple[str, ...] = ("content:reported-total-value",),
    evidence_refs: tuple[str, ...] = (EVIDENCE_ID,),
    observation_kind: ObservationKind = ObservationKind.SUPPORT,
    support_status: SupportStatus = SupportStatus.SUPPORTS,
    claim_or_value: object = "1,284 records",
    contract_version: str | None = None,
    contract_digest: str | None = None,
    question_meaning_record_id: str | None = None,
    question_meaning_record_digest: str | None = None,
    component_revision: str | None = None,
    component_contract_digest: str | None = None,
    answer_component_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> SemanticObservation:
    component_ref = accepted["accepted_answer_component_refs"][0]
    return SemanticObservation(
        observation_id=observation_id,
        observation_kind=observation_kind,
        question_meaning_record_id=(
            question_meaning_record_id
            if question_meaning_record_id is not None
            else accepted["parent_question_meaning_record_id"]
        ),
        question_meaning_record_digest=(
            question_meaning_record_digest
            if question_meaning_record_digest is not None
            else accepted["parent_question_meaning_record_digest"]
        ),
        contract_version=(
            contract_version if contract_version is not None else accepted["accepted_contract_version"]
        ),
        contract_digest=(
            contract_digest if contract_digest is not None else accepted["accepted_contract_digest"]
        ),
        answer_component_id=answer_component_id or component_ref["component_id"],
        component_revision=component_revision or component_ref["component_revision"],
        component_contract_digest=component_contract_digest or component_ref["component_digest"],
        evidence_refs=evidence_refs,
        content_refs=content_refs,
        support_kind=SupportDirectness.DIRECT,
        directness=SupportDirectness.DIRECT,
        support_status=support_status,
        claim_or_value=claim_or_value,
        normalization_fit="annual record counts",
        scope_fit="calendar year 2026",
        assumption_fit="uses source wording without runtime admission",
        inference_depth=0,
        candidate_caveats=("Currentness remains evidence-bound.",),
        candidate_followup_gaps=("Verify against admitted evidence in a later reducer.",),
        candidate_contract_amendment_notes=("Candidate only; does not mutate contract.",),
        metadata=metadata if metadata is not None else {"safe_review_note": "passive observation"},
    )


def _admit(
    kernel: RunKernel,
    observation: SemanticObservation,
    content_refs: tuple[SanitizedContentReference, ...],
    *,
    observation_id: str | None = None,
    observation_digest: str | None = None,
    component_revision: str | None = None,
    component_digest: str | None = None,
    answer_component_id: str | None = None,
    payload: dict[str, object] | None = None,
) -> Observation:
    accepted = kernel.state.initial_answer_contract
    component_ref = accepted["accepted_answer_component_refs"][0]
    action = kernel.authorize_semantic_observation_admission(
        semantic_observation_id=observation_id if observation_id is not None else observation.observation_id,
        semantic_observation_digest=(
            observation_digest if observation_digest is not None else observation.observation_digest
        ),
        answer_component_id=answer_component_id or component_ref["component_id"],
        component_revision=component_revision or component_ref["component_revision"],
        component_digest=component_digest or component_ref["component_digest"],
    )
    if payload is None:
        payload = {
            "semantic_observation": observation.to_dict(),
            "sanitized_content_references": [ref.to_dict() for ref in content_refs],
        }
    reduce_observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEMANTIC_OBSERVATION_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    kernel.reduce(reduce_observation)
    return reduce_observation


def test_authorized_admission_creates_canonical_state_projection_history() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    _admit(kernel, observation, (content_ref,))

    state = kernel.state.semantic_observation_admission_state
    projection = kernel.state.semantic_observation_admission_projection
    assert state["schema_version"] == SEMANTIC_OBSERVATION_ADMISSION_SCHEMA_VERSION
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["authorized_action_id"]
    assert state["observation_id"] == observation.observation_id
    assert state["observation_digest"] == observation.observation_digest
    assert state["accepted_contract_digest"] == accepted["accepted_contract_digest"]
    assert state["accepted_contract_version"] == accepted["accepted_contract_version"]
    assert state["answer_component_id"] == COMPONENT_ID
    assert state["evidence_refs"] == [EVIDENCE_ID]
    assert state["content_refs"] == ["content:reported-total-value"]
    assert state["support_status"] == "supports"
    assert state["lineage"]["created_by"] == "RunKernel.SemanticObservationAdmission"
    assert state["lineage"]["reducer_action_id"] == state["authorized_action_id"]
    assert state["lineage"]["accepted_contract_digest"] == accepted["accepted_contract_digest"]
    assert state["admission_digest"]
    assert kernel.state.semantic_observation_admission_history[-1] == projection
    assert kernel.state.projections[SEMANTIC_OBSERVATION_ADMISSION_STAGE] == projection
    assert kernel.state.stage_statuses[SEMANTIC_OBSERVATION_ADMISSION_STAGE] is RunStageStatus.COMPLETED


def test_admission_requires_existing_initial_answer_contract() -> None:
    kernel = RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)
    with pytest.raises(RunKernelTransitionError, match="accepted initial answer contract"):
        kernel.authorize_semantic_observation_admission(
            semantic_observation_id="observation:x",
            semantic_observation_digest="d" * 16,
            answer_component_id=COMPONENT_ID,
            component_revision="1",
            component_digest="c" * 16,
            accepted_contract_digest="a" * 16,
            accepted_contract_version="0.1-passive",
        )


def test_builder_requires_accepted_contract() -> None:
    with pytest.raises(SemanticObservationAdmissionError, match="accepted initial answer contract"):
        build_semantic_observation_admission_state(
            action_id="action:sem-06",
            action_inputs={},
            observation_payload={"semantic_observation": {"observation_id": "x"}},
            accepted_contract={},
            evidence_ledger_projection={},
            run_id=RUN_ID,
            request_id=REQUEST_ID,
        )


def test_observation_id_digest_and_action_binding_is_exact() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    with pytest.raises(RunKernelTransitionError, match="semantic_observation_id binding"):
        _admit(kernel, observation, (content_ref,), observation_id="observation:not-this-one")

    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    with pytest.raises(RunKernelTransitionError, match="semantic_observation_digest binding"):
        _admit(kernel, observation, (content_ref,), observation_digest="0" * 64)


def test_recomputed_observation_digest_rejects_tampered_observation_payload() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    tampered = observation.to_dict()
    # Keep the declared (stale) observation_digest but alter the claim content.
    tampered["claim_or_value"] = "9,999 records"
    payload = {
        "semantic_observation": tampered,
        "sanitized_content_references": [content_ref.to_dict()],
    }
    with pytest.raises(RunKernelTransitionError, match="observation digest does not match"):
        _admit(kernel, observation, (content_ref,), payload=payload)


def test_recomputed_content_digest_rejects_tampered_content_payload() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    tampered_ref = content_ref.to_dict()
    # Keep the declared (stale) content_digest but alter the bounded text.
    tampered_ref["bounded_text"] = "The 2026 reported total is 9,999 records."
    payload = {
        "semantic_observation": observation.to_dict(),
        "sanitized_content_references": [tampered_ref],
    }
    with pytest.raises(RunKernelTransitionError, match="content digest does not match"):
        _admit(kernel, observation, (content_ref,), payload=payload)


def test_observation_contract_version_or_digest_mismatch_is_rejected() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted, contract_digest="f" * 64)
    with pytest.raises(RunKernelTransitionError, match="contract_digest does not match"):
        _admit(kernel, observation, (content_ref,))

    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted, contract_version="9.9-other")
    with pytest.raises(RunKernelTransitionError, match="contract_version does not match"):
        _admit(kernel, observation, (content_ref,))


def test_component_id_revision_digest_mismatch_is_rejected() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted, component_revision="99")
    with pytest.raises(RunKernelTransitionError, match="component_revision"):
        _admit(kernel, observation, (content_ref,), component_revision="99")

    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted, component_contract_digest="e" * 64)
    with pytest.raises(RunKernelTransitionError, match="component_contract_digest does not match"):
        _admit(kernel, observation, (content_ref,), component_digest="e" * 64)


def test_missing_content_ref_is_rejected() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted, content_refs=("content:does-not-exist",))
    with pytest.raises(RunKernelTransitionError, match="missing content ref"):
        _admit(kernel, observation, (content_ref,))


def test_foreign_or_missing_evidence_custody_ref_is_rejected() -> None:
    # No evidence ledger seeding: the cited custody ref is foreign/missing.
    kernel, accepted = _start_accepted_kernel()
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    with pytest.raises(RunKernelTransitionError, match="absent from EvidenceLedger custody"):
        _admit(kernel, observation, (content_ref,))

    # Seeding a different candidate id does not vouch for the cited ref.
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel, candidate_id="evidence:some-other-record")
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    with pytest.raises(RunKernelTransitionError, match="absent from EvidenceLedger custody"):
        _admit(kernel, observation, (content_ref,))


def test_duplicate_observation_id_or_digest_or_reduction_is_rejected() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    reduce_observation = _admit(kernel, observation, (content_ref,))

    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(reduce_observation)

    # A second admission of the same observation id/digest is rejected.
    with pytest.raises(RunKernelTransitionError, match="already admitted"):
        _admit(kernel, observation, (content_ref,))


def test_support_bearing_observation_requires_answer_bearing_content_refs() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    observation = _observation(accepted, content_refs=())
    with pytest.raises(RunKernelTransitionError, match="content ref"):
        _admit(kernel, observation, ())


def test_candidate_caveats_gaps_and_amendment_notes_remain_candidate_only() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    _admit(kernel, observation, (content_ref,))

    state = kernel.state.semantic_observation_admission_state
    assert state["candidate_caveats"] == ["Currentness remains evidence-bound."]
    assert state["candidate_followup_gaps"] == ["Verify against admitted evidence in a later reducer."]
    assert state["candidate_contract_amendment_notes"] == ["Candidate only; does not mutate contract."]
    for flag in ("amendment_created", "followup_authorized", "coverage_created"):
        assert state[flag] is False


def test_no_coverage_amendment_sufficiency_packet_author_search_followup_state() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    _admit(kernel, observation, (content_ref,))

    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_judgment == {}
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_authorization_state == {}

    projection = kernel.state.semantic_observation_admission_projection
    for flag in (
        "coverage_created",
        "component_satisfied",
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


def test_projection_and_admission_digest_are_deterministic() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()

    inputs = {
        "semantic_observation_id": observation.observation_id,
        "semantic_observation_digest": observation.observation_digest,
        "accepted_contract_digest": accepted["accepted_contract_digest"],
        "accepted_contract_version": accepted["accepted_contract_version"],
        "answer_component_id": COMPONENT_ID,
        "component_revision": "1",
        "component_digest": accepted["accepted_answer_component_refs"][0]["component_digest"],
        "request_id": REQUEST_ID,
    }
    payload = {
        "semantic_observation": observation.to_dict(),
        "sanitized_content_references": [content_ref.to_dict()],
    }
    first = build_semantic_observation_admission_state(
        action_id="action:sem-06",
        action_inputs=inputs,
        observation_payload=deepcopy(payload),
        accepted_contract=accepted,
        evidence_ledger_projection=ledger_projection,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    second = build_semantic_observation_admission_state(
        action_id="action:sem-06",
        action_inputs=inputs,
        observation_payload=deepcopy(payload),
        accepted_contract=accepted,
        evidence_ledger_projection=ledger_projection,
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    assert first["admission_digest"] == second["admission_digest"]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    first_projection = build_semantic_observation_admission_projection(admission_state=first)
    second_projection = build_semantic_observation_admission_projection(admission_state=second)
    assert json.dumps(first_projection, sort_keys=True) == json.dumps(second_projection, sort_keys=True)
    assert first_projection["admission_digest"] == first["admission_digest"]


def test_sensitive_fields_are_scrubbed_and_closed_authority_is_rejected() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(
        accepted,
        metadata={"safe_review_note": "kept", "raw_prompt": "SENTINEL_RAW_PROMPT"},
    )

    _admit(kernel, observation, (content_ref,))
    encoded = json.dumps(kernel.state.semantic_observation_admission_state, sort_keys=True)
    assert "SENTINEL_RAW_PROMPT" not in encoded
    assert "raw_prompt" not in encoded

    # An observation payload carrying a closed authority surface is rejected.
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    tainted_observation = observation.to_dict()
    # "coverage" is a closed authority surface caught by the forbidden-fields
    # check (it is not one of the pre-reconstruction posture flags).
    tainted_observation["coverage"] = {"decision": "covered"}
    tainted = {
        "semantic_observation": tainted_observation,
        "sanitized_content_references": [content_ref.to_dict()],
    }
    with pytest.raises(RunKernelTransitionError, match="closed authority fields"):
        _admit(kernel, observation, (content_ref,), payload=tainted)


def test_observation_with_coverage_decision_is_rejected_before_reconstruction() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)
    tainted = observation.to_dict()
    tainted["coverage_decision"] = True
    payload = {
        "semantic_observation": tainted,
        "sanitized_content_references": [content_ref.to_dict()],
    }
    with pytest.raises(RunKernelTransitionError, match="closed authority posture"):
        _admit(kernel, observation, (content_ref,), payload=payload)


def test_observation_with_accepted_authority_or_runtime_behavior_changed_is_rejected() -> None:
    for flag in ("accepted_authority", "runtime_behavior_changed"):
        kernel, accepted = _start_accepted_kernel()
        _seed_evidence_ledger(kernel)
        content_ref = _content_ref(accepted)
        observation = _observation(accepted)
        tainted = observation.to_dict()
        tainted[flag] = True
        payload = {
            "semantic_observation": tainted,
            "sanitized_content_references": [content_ref.to_dict()],
        }
        with pytest.raises(RunKernelTransitionError, match="closed authority posture"):
            _admit(kernel, observation, (content_ref,), payload=payload)


def test_observation_with_component_satisfied_or_final_answer_authority_is_rejected() -> None:
    for flag in ("component_satisfied", "final_answer_authority"):
        kernel, accepted = _start_accepted_kernel()
        _seed_evidence_ledger(kernel)
        content_ref = _content_ref(accepted)
        observation = _observation(accepted)
        tainted = observation.to_dict()
        tainted[flag] = True
        payload = {
            "semantic_observation": tainted,
            "sanitized_content_references": [content_ref.to_dict()],
        }
        with pytest.raises(RunKernelTransitionError, match="closed authority posture"):
            _admit(kernel, observation, (content_ref,), payload=payload)


def test_content_ref_with_unsafe_retention_or_authority_posture_is_rejected() -> None:
    for flag in ("raw_content_retained", "accepted_authority"):
        kernel, accepted = _start_accepted_kernel()
        _seed_evidence_ledger(kernel)
        content_ref = _content_ref(accepted)
        observation = _observation(accepted)
        tainted_ref = content_ref.to_dict()
        tainted_ref[flag] = True
        payload = {
            "semantic_observation": observation.to_dict(),
            "sanitized_content_references": [tainted_ref],
        }
        with pytest.raises(RunKernelTransitionError, match="unsafe retention/authority posture"):
            _admit(kernel, observation, (content_ref,), payload=payload)


def test_content_ref_with_sanitized_or_bounded_disabled_is_rejected() -> None:
    for flag in ("sanitized", "bounded"):
        kernel, accepted = _start_accepted_kernel()
        _seed_evidence_ledger(kernel)
        content_ref = _content_ref(accepted)
        observation = _observation(accepted)
        tainted_ref = content_ref.to_dict()
        tainted_ref[flag] = False
        payload = {
            "semantic_observation": observation.to_dict(),
            "sanitized_content_references": [tainted_ref],
        }
        with pytest.raises(RunKernelTransitionError, match="unsafe retention/authority posture"):
            _admit(kernel, observation, (content_ref,), payload=payload)


def test_clean_observation_and_content_ref_still_admits_after_posture_guard() -> None:
    kernel, accepted = _start_accepted_kernel()
    _seed_evidence_ledger(kernel)
    content_ref = _content_ref(accepted)
    observation = _observation(accepted)

    _admit(kernel, observation, (content_ref,))

    state = kernel.state.semantic_observation_admission_state
    assert state["canonical_state"] is True
    assert state["observation_id"] == observation.observation_id


def test_static_guard_keeps_live_and_authority_surfaces_closed() -> None:
    source = RUNTIME_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_import_roots = {
        "core.pipeline_orchestrator",
        "core.run_kernel",
        "core.author_execution_runtime",
        "core.final_answer_packet",
        "core.final_answer_packet_runtime",
        "core.retrieval_dispatch_runtime",
        "core.component_coverage_record",
        "core.contract_amendment_record",
        "core.evidence_ledger",
        "openai",
        "requests",
        "httpx",
        "urllib",
        "dotenv",
        "subprocess",
        "os",
    }
    forbidden_called_names = {
        "run_pipeline",
        "authorize_",
        "execute_author",
        "search_web",
        "retrieve",
        "read_url",
        "render_citation",
        "live_provider",
        "reduce_coverage",
    }
    imported_names: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called_names.add(func.id)
            elif isinstance(func, ast.Attribute):
                called_names.add(func.attr)

    assert imported_names.isdisjoint(forbidden_import_roots)
    assert called_names.isdisjoint(forbidden_called_names)

    kernel_source = RUN_KERNEL.read_text(encoding="utf-8")
    assert "SEMANTIC_OBSERVATION_ADMIT" in kernel_source
    assert "build_semantic_observation_admission_state" in kernel_source
    for forbidden in ("requests.", "openai", "brave_reconnaissance", ".env"):
        assert forbidden not in source
