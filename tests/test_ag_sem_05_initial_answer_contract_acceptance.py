from __future__ import annotations

import ast
import json
from copy import deepcopy
from pathlib import Path

import pytest

from core.initial_answer_contract_acceptance_runtime import (
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_SCHEMA_VERSION,
    InitialAnswerContractAcceptanceError,
    build_initial_answer_contract_acceptance_projection,
    build_initial_answer_contract_acceptance_state,
)
from core.run_kernel import (
    INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE,
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

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "initial_answer_contract_acceptance_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"

RUN_ID = "run:sem-05-offline"
REQUEST_ID = "request:sem-05"


def _metric_slot() -> SemanticSlot:
    return SemanticSlot(
        slot_id="slot:metric",
        slot_kind=SemanticSlotKind.METRIC,
        status=SemanticSlotStatus.EXPLICIT,
        selected_value="active accounts",
        materiality=Materiality.MATERIAL,
    )


def _time_period_slot() -> SemanticSlot:
    return SemanticSlot(
        slot_id="slot:time-period",
        slot_kind=SemanticSlotKind.TIME_PERIOD,
        status=SemanticSlotStatus.EXPLICIT,
        selected_value="first quarter 2026",
        materiality=Materiality.MATERIAL,
    )


def _ambiguous_geography_slot() -> SemanticSlot:
    return SemanticSlot(
        slot_id="slot:geography",
        slot_kind=SemanticSlotKind.GEOGRAPHY,
        status=SemanticSlotStatus.AMBIGUOUS,
        candidate_values=("global", "primary region"),
        materiality=Materiality.MATERIAL,
        user_confirmation_required=True,
    )


def _component() -> AnswerComponentContract:
    return AnswerComponentContract(
        component_id="component:reported-value",
        component_revision="1",
        user_facing_label="Reported value",
        user_facing_question="What is the reported value for the requested metric?",
        requirement_posture=RequirementPosture.REQUIRED,
        acceptance_criteria=("state the bounded value", "bind it to evidence"),
        semantic_slot_ids=("slot:metric", "slot:time-period"),
        source_obligation_candidate_ids=("obligation:primary-source",),
        allowed_support_kinds=(SupportKind.DIRECT,),
        max_inference_depth=0,
        mandatory_caveats=("Value remains evidence-bound.",),
        prohibited_upgrades=("Do not replace the value with an estimate.",),
        materiality=Materiality.MATERIAL,
    )


def _qmr(
    *,
    slots: tuple[SemanticSlot, ...] | None = None,
    components: tuple[AnswerComponentContract, ...] | None = None,
    metadata: dict[str, object] | None = None,
) -> QuestionMeaningRecord:
    return QuestionMeaningRecord(
        record_id="qmr:reported-value",
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        request_digest="request-digest-sem-05",
        requested_mode="balanced",
        resolver_kind=ResolverKind.PASSIVE_PROPOSAL,
        resolver_version="ag-sem-05-test",
        intent="Answer the reported-value question.",
        requested_output="Concise answer with primary-source support.",
        semantic_slots=slots if slots is not None else (_metric_slot(), _time_period_slot()),
        answer_components=components if components is not None else (_component(),),
        metadata=metadata if metadata is not None else {"safe_note": "kept"},
    ).require_valid()


def _start_kernel() -> RunKernel:
    return RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)


def _accept(
    kernel: RunKernel,
    qmr: QuestionMeaningRecord,
    *,
    parent_id: str | None = None,
    parent_digest: str | None = None,
    payload: dict[str, object] | None = None,
) -> Observation:
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=parent_id if parent_id is not None else qmr.record_id,
        parent_proposal_digest=parent_digest if parent_digest is not None else qmr.record_digest,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
        status=RunStageStatus.COMPLETED,
        payload=payload if payload is not None else {"question_meaning_record": qmr.to_dict()},
    )
    kernel.reduce(observation)
    return observation


def test_authorized_acceptance_creates_canonical_state() -> None:
    kernel = _start_kernel()
    qmr = _qmr()

    _accept(kernel, qmr)

    state = kernel.state.initial_answer_contract
    projection = kernel.state.initial_answer_contract_projection
    assert state["schema_version"] == INITIAL_ANSWER_CONTRACT_ACCEPTANCE_SCHEMA_VERSION
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["authorized_action_id"]
    assert state["accepted_contract_version"]
    assert state["accepted_contract_digest"]
    assert kernel.state.initial_answer_contract_history[-1] == projection
    assert kernel.state.projections[INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE] == projection
    assert kernel.state.stage_statuses[INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE] is (RunStageStatus.COMPLETED)


def test_parent_question_meaning_record_id_and_digest_are_bound_exactly() -> None:
    kernel = _start_kernel()
    qmr = _qmr()

    _accept(kernel, qmr)

    state = kernel.state.initial_answer_contract
    assert state["parent_question_meaning_record_id"] == qmr.record_id
    assert state["parent_question_meaning_record_digest"] == qmr.record_digest
    assert state["parent_proposal_schema_version"] == qmr.schema_version
    assert state["lineage"]["parent_proposal_digest"] == qmr.record_digest
    assert state["lineage"]["reducer_action_id"] == state["authorized_action_id"]
    assert state["lineage"]["created_by"] == "RunKernel.InitialAnswerContract"


def test_answer_component_refs_preserve_id_revision_digest_and_posture() -> None:
    kernel = _start_kernel()
    component = _component()
    qmr = _qmr(components=(component,))

    _accept(kernel, qmr)

    refs = kernel.state.initial_answer_contract["accepted_answer_component_refs"]
    assert len(refs) == 1
    ref = refs[0]
    assert ref["component_id"] == component.component_id
    assert ref["component_revision"] == component.component_revision
    assert ref["component_digest"] == component.component_digest
    assert ref["requirement_posture"] == "required"
    assert ref["materiality"] == "material"
    assert ref["mandatory_caveats"] == ["Value remains evidence-bound."]
    assert ref["prohibited_upgrades"] == ["Do not replace the value with an estimate."]
    assert ref["source_obligation_candidate_ids"] == ["obligation:primary-source"]
    assert ref["allowed_support_kinds"] == ["direct"]


def test_material_unresolved_slots_are_preserved_not_resolved() -> None:
    kernel = _start_kernel()
    qmr = _qmr(
        slots=(_metric_slot(), _time_period_slot(), _ambiguous_geography_slot()),
    )

    _accept(kernel, qmr)

    slots = {ref["slot_id"]: ref for ref in kernel.state.initial_answer_contract["accepted_semantic_slot_refs"]}
    geography = slots["slot:geography"]
    assert geography["status"] == "ambiguous"
    assert geography["materiality"] == "material"
    assert geography["unresolved_material"] is True
    # The acceptance bridge must never resolve a material ambiguity.
    assert "selected_value" not in geography
    assert kernel.state.initial_answer_contract["material_ambiguity_count"] == 1
    assert kernel.state.initial_answer_contract["material_ambiguity_resolved"] is False
    assert kernel.state.initial_answer_contract["material_ambiguity_preserved"] is True
    # An explicit, already-selected slot keeps its selected value.
    assert slots["slot:metric"]["selected_value"] == "active accounts"


def test_empty_or_invalid_answer_components_are_rejected() -> None:
    qmr = _qmr()
    base_payload = qmr.to_dict()

    empty_payload = deepcopy(base_payload)
    empty_payload["answer_components"] = []
    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="at least one accepted answer component"):
        _accept(kernel, qmr, payload={"question_meaning_record": empty_payload})

    missing_field_payload = deepcopy(base_payload)
    missing_field_payload["answer_components"][0].pop("component_digest")
    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="component_digest"):
        _accept(kernel, qmr, payload={"question_meaning_record": missing_field_payload})

    duplicate_payload = deepcopy(base_payload)
    duplicate_payload["answer_components"] = [
        deepcopy(base_payload["answer_components"][0]),
        deepcopy(base_payload["answer_components"][0]),
    ]
    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="duplicate answer component"):
        _accept(kernel, qmr, payload={"question_meaning_record": duplicate_payload})


def test_mismatched_proposal_action_run_request_binding_is_rejected() -> None:
    qmr = _qmr()

    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="digest binding"):
        _accept(kernel, qmr, parent_digest="not-the-real-digest")

    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="id binding"):
        _accept(kernel, qmr, parent_id="qmr:not-this-one")

    wrong_run_payload = qmr.to_dict()
    wrong_run_payload["run_id"] = "run:some-other-run"
    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="run_id does not match"):
        _accept(kernel, qmr, payload={"question_meaning_record": wrong_run_payload})

    wrong_request_payload = qmr.to_dict()
    wrong_request_payload["request_id"] = "request:other"
    kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="request_id does not match"):
        _accept(kernel, qmr, payload={"question_meaning_record": wrong_request_payload})


def test_duplicate_and_stale_reduction_is_rejected() -> None:
    kernel = _start_kernel()
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

    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(observation)

    # A second distinct acceptance action cannot create canonical state twice.
    with pytest.raises(RunKernelTransitionError, match="already been accepted"):
        _accept(kernel, qmr)


def test_no_coverage_amendment_sufficiency_packet_author_search_followup_state() -> None:
    kernel = _start_kernel()
    qmr = _qmr()

    _accept(kernel, qmr)

    assert kernel.state.run_contract == {}
    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_judgment == {}
    assert kernel.state.sufficiency_judgment == {}
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_authorization_state == {}
    assert kernel.state.evidence_ledger.to_projection().to_dict().get("requirement_count", 0) == 0

    projection = kernel.state.initial_answer_contract_projection
    for flag in (
        "coverage_created",
        "amendment_created",
        "semantic_observation_admitted",
        "sufficiency_decided",
        "search_judgment_decided",
        "query_plan_activated",
        "search_work_plan_activated",
        "followup_authorized",
        "final_answer_packet_created",
        "author_input_created",
        "citation_behavior_changed",
        "provider_search_behavior_changed",
        "runtime_behavior_changed",
    ):
        assert projection[flag] is False


def test_projection_and_digest_are_deterministic() -> None:
    qmr = _qmr()

    first = build_initial_answer_contract_acceptance_state(
        action_id="run:sem-05-offline:action:1:initial_answer_contract_accept",
        action_inputs={
            "parent_question_meaning_record_id": qmr.record_id,
            "parent_proposal_digest": qmr.record_digest,
            "request_id": REQUEST_ID,
        },
        question_meaning_record=qmr.to_dict(),
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )
    second = build_initial_answer_contract_acceptance_state(
        action_id="run:sem-05-offline:action:1:initial_answer_contract_accept",
        action_inputs={
            "parent_question_meaning_record_id": qmr.record_id,
            "parent_proposal_digest": qmr.record_digest,
            "request_id": REQUEST_ID,
        },
        question_meaning_record=qmr.to_dict(),
        run_id=RUN_ID,
        request_id=REQUEST_ID,
    )

    assert first["accepted_contract_digest"] == second["accepted_contract_digest"]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    first_projection = build_initial_answer_contract_acceptance_projection(acceptance_state=first)
    second_projection = build_initial_answer_contract_acceptance_projection(acceptance_state=second)
    assert json.dumps(first_projection, sort_keys=True) == json.dumps(second_projection, sort_keys=True)
    assert first_projection["accepted_contract_digest"] == first["accepted_contract_digest"]


def test_sensitive_metadata_is_scrubbed_and_closed_authority_is_rejected() -> None:
    kernel = _start_kernel()
    qmr = _qmr(metadata={"safe_note": "kept", "raw_prompt": "SENTINEL_RAW_PROMPT"})

    _accept(kernel, qmr)

    encoded = json.dumps(kernel.state.initial_answer_contract, sort_keys=True)
    assert "SENTINEL_RAW_PROMPT" not in encoded
    assert "raw_prompt" not in encoded
    assert "[redacted]" not in encoded

    # A proposal payload carrying a closed authority surface is rejected.
    tainted_payload = qmr.to_dict()
    tainted_payload["sufficiency_judgment"] = {"decision": "sufficient"}
    reject_kernel = _start_kernel()
    with pytest.raises(RunKernelTransitionError, match="closed authority fields"):
        _accept(
            reject_kernel,
            qmr,
            payload={"question_meaning_record": tainted_payload},
        )


def test_missing_proposal_payload_is_rejected() -> None:
    kernel = _start_kernel()
    qmr = _qmr()
    with pytest.raises(RunKernelTransitionError, match="question_meaning_record"):
        _accept(kernel, qmr, payload={"unrelated": "value"})


def test_builder_rejects_non_passive_or_canonical_proposal() -> None:
    qmr = _qmr()
    canonical_payload = qmr.to_dict()
    canonical_payload["canonical_state"] = True
    with pytest.raises(InitialAnswerContractAcceptanceError, match="canonical state"):
        build_initial_answer_contract_acceptance_state(
            action_id="action:1",
            action_inputs={
                "parent_question_meaning_record_id": qmr.record_id,
                "parent_proposal_digest": qmr.record_digest,
            },
            question_meaning_record=canonical_payload,
            run_id=RUN_ID,
            request_id=REQUEST_ID,
        )


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
        "core.semantic_observation_foundation",
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
    assert "INITIAL_ANSWER_CONTRACT_ACCEPT" in kernel_source
    assert "build_initial_answer_contract_acceptance_state" in kernel_source
    for forbidden in ("requests.", "openai", "brave_reconnaissance", ".env"):
        assert forbidden not in source
