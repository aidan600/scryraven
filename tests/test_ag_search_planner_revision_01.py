from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.run_kernel import (
    SEARCH_PLANNER_REVISION_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.scout_disambiguation_runtime import (
    ScoutDisambiguationInput,
    execute_scout_disambiguation_action,
)
from core.search_planner_revision_runtime import (
    SEARCH_PLANNER_REVISION_OWNER,
    SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION,
    SearchPlannerRevisionInput,
    SearchPlannerRevisionRuntimeError,
    build_search_planner_revision_observation_payload,
    contract_ref_from_contract,
    execute_search_planner_revision_action,
    planner_ref_from_search_planner_state,
    scout_ref_from_scout_report_state,
)
from core.search_planner_runtime import (
    SEARCH_PLANNER_SCHEMA_VERSION,
    SearchPlannerInput,
    execute_search_planner_action,
)
from core.search_planner_runtime import (
    contract_ref_from_contract as planner_contract_ref_from_contract,
)

ROOT = Path(__file__).resolve().parents[1]
REVISION_RUNTIME = ROOT / "core" / "search_planner_revision_runtime.py"
REVISION_ADAPTER = ROOT / "core" / "search_planner_revision_model_adapter.py"
REVISION_PROMPT = ROOT / "core" / "search_planner_revision_model_prompt.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "roadmap" / "SEARCHOS_QUERY_STRATEGY_AND_RECON_CONVERGENCE_01.md",
)

RUN_ID = "run:ag-search-planner-revision-01"
REQUEST_ID = "request:ag-search-planner-revision-01"
QUERY = "What is the current official Example Permit threshold in 2026?"
COMPONENT_ID = "component:official-threshold"
CONSUMED_DIMENSION_IDS = ["dim:entity"]
CONSUMED_HINT_IDS = ["hint:scout-query:official:organic:1"]

FALSE_FLAGS = {
    "scout_hints_are_evidence": False,
    "evidence_admitted": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "fetch_read_retrieval_behavior_changed": False,
    "search_executor_runtime_activated": False,
    "search_work_plan_constructed": False,
    "contract_mutation_applied": False,
    "initial_answer_contract_mutated": False,
    "current_answer_contract_mutated": False,
    "amendment_admitted": False,
    "amendment_applied": False,
    "semantic_observation_admitted": False,
    "component_coverage_reduced": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "live_validation_run": False,
    "live_provider_calls_executed": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
}


class DeterministicPlannerAdapter:
    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_result()


class FakeScoutAdapter:
    def __init__(self, result: Mapping[str, Any] | None = None) -> None:
        self.result = dict(result or _scout_result())

    def produce(self, scout_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return deepcopy(self.result)


class FakeRevisionAdapter:
    def __init__(self, result: Mapping[str, Any] | None = None) -> None:
        self.result = dict(result or _revision_result())
        self.calls: list[dict[str, Any]] = []

    def produce(self, revision_input: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls.append(dict(revision_input))
        result = deepcopy(self.result)
        result["consumed_ambiguity_dimension_ids"] = list(
            revision_input["consumed_ambiguity_dimension_ids"]
        )
        result["consumed_scout_hint_ids"] = list(
            revision_input["consumed_scout_hint_ids"]
        )
        return result


def _planner_result() -> dict[str, Any]:
    return {
        "question_meaning_summary": (
            "Determine the official current threshold while preserving material "
            "identity and jurisdiction ambiguity."
        ),
        "requested_output": "Concise answer with official-current source support.",
        "semantic_slots": [
            {
                "slot_id": "slot:program",
                "slot_kind": "entity",
                "status": "ambiguous",
                "candidate_values": ["Example Permit", "Example Permit Renewal"],
                "materiality": "material",
                "user_confirmation_required": True,
            },
            {
                "slot_id": "slot:jurisdiction",
                "slot_kind": "jurisdiction",
                "status": "unresolved",
                "candidate_values": ["State A", "State B"],
                "materiality": "material",
                "user_confirmation_required": True,
            },
            {
                "slot_id": "slot:time-period",
                "slot_kind": "time_period",
                "status": "explicit",
                "selected_value": "2026",
                "materiality": "material",
            },
        ],
        "answer_components": [
            {
                "component_id": COMPONENT_ID,
                "component_revision": "1",
                "user_facing_label": "Official threshold",
                "user_facing_question": (
                    "What is the official current filing threshold for the "
                    "requested program?"
                ),
                "requirement_posture": "required",
                "acceptance_criteria": [
                    "identify the likely program and jurisdiction",
                    "preserve official-current source obligations",
                ],
                "semantic_slot_ids": [
                    "slot:program",
                    "slot:jurisdiction",
                    "slot:time-period",
                ],
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "allowed_support_kinds": ["direct"],
                "max_inference_depth": 0,
                "mandatory_caveats": ["Keep ambiguity visible until resolved."],
                "prohibited_upgrades": ["Do not cite Scout hints as evidence."],
                "materiality": "material",
            }
        ],
        "source_obligation_candidates": [
            {
                "candidate_id": "obligation:official-current",
                "obligation_kind": "official_current_source",
                "component_candidate_ids": [COMPONENT_ID],
                "strictness": "required",
            }
        ],
        "component_search_requirements": [
            {
                "component_id": COMPONENT_ID,
                "requirement_id": "searchreq:official-current-threshold",
                "requirement_summary": "Find the official current threshold source.",
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "preferred_source_kinds": ["official"],
                "recency_requirement": "current for 2026",
            }
        ],
        "material_ambiguity_posture": "material_ambiguity_present",
        "mandatory_caveats": ["Scout may only produce direction hints."],
        "prohibited_upgrades": ["Do not infer final answer from snippets."],
        "normalization_obligations": ["Normalize the effective year to 2026."],
        "assumptions": [],
        "unsupported_outputs": ["No final answer is produced by the planner."],
    }


def _scout_dimensions() -> list[dict[str, Any]]:
    return [
        {
            "dimension_id": "dim:entity",
            "dimension_kind": "entity_identity",
            "summary": "Which Example Permit identity is likely?",
            "related_semantic_slot_ids": ["slot:program"],
            "priority": 1,
            "status": "open",
            "materiality": "material",
        },
        {
            "dimension_id": "dim:jurisdiction",
            "dimension_kind": "jurisdiction",
            "summary": "Which jurisdiction is likely?",
            "related_semantic_slot_ids": ["slot:jurisdiction"],
            "priority": 2,
            "status": "open",
            "materiality": "material",
        },
    ]


def _scout_result() -> dict[str, Any]:
    return {
        "scout_queries": [
            {
                "query_id": "scout-query:official",
                "safe_query_text": "Example Permit official 2026 threshold",
                "query_kind": "official_domain_probe",
                "priority": 1,
                "related_dimension_ids": ["dim:entity"],
                "execution_status": "executed_by_fake_adapter",
                "search_vertical": "search",
                "provider_hint": "serper",
                "not_live": True,
                "provider_payload_retained": False,
            }
        ],
        "organic_results": [
            {
                "query_id": "scout-query:official",
                "related_dimension_ids": ["dim:entity"],
                "title": "Example Permit - Official Threshold",
                "link": "https://official.example.gov/permit/threshold",
                "snippet": "Official current threshold information.",
                "position": 1,
                "date": "2026-01-01",
                "source": "Official Example",
                "official_target_hint": "Likely official permit threshold page.",
            }
        ],
        "candidate_interpretations": [
            {
                "interpretation_id": "interp:official-permit",
                "summary": "The user likely means Example Permit.",
                "related_dimension_ids": ["dim:entity"],
                "supporting_hint_ids": CONSUMED_HINT_IDS,
            }
        ],
        "recommended_planner_revision_inputs": {
            "resolved_candidate_interpretations": ["interp:official-permit"],
            "unresolved_ambiguity_dimensions": ["dim:jurisdiction"],
            "suggested_slot_updates": [
                {"slot_id": "slot:program", "candidate_value": "Example Permit"}
            ],
            "suggested_source_obligation_focus": ["official_current_source"],
            "suggested_caveats": ["Jurisdiction remains unresolved."],
        },
        "unresolved_ambiguities": [
            {
                "unresolved_id": "unresolved:jurisdiction",
                "summary": "Jurisdiction still needs planner handling.",
                "related_dimension_ids": ["dim:jurisdiction"],
            }
        ],
        "confidence_posture": "directional",
        "disambiguation_posture": "partially_resolved_report_only",
    }


def _revision_result(
    *,
    operation_kind: str = "add_caveat",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "revised_question_meaning_summary": (
            "Use Scout only to focus the official-current search target while "
            "keeping unresolved jurisdiction visible."
        ),
        "semantic_slot_updates": [
            {
                "slot_id": "slot:program",
                "status": "ambiguous",
                "candidate_values": ["Example Permit", "Example Permit Renewal"],
                "revision_note": "Scout direction favors Example Permit but is not evidence.",
            }
        ],
        "answer_component_updates": [
            {
                "component_id": COMPONENT_ID,
                "revision_note": "Keep the component pending official-current support.",
            }
        ],
        "component_search_requirement_updates": [
            {
                "component_id": COMPONENT_ID,
                "requirement_id": "searchreq:official-current-threshold:revision",
                "requirement_summary": "Focus later search on official Example Permit pages.",
                "source_obligation_candidate_ids": ["obligation:official-current"],
                "preferred_source_kinds": ["official"],
                "must_not_execute": True,
                "search_executed": False,
                "source_obligation_satisfied": False,
            }
        ],
        "mandatory_caveats": ["Scout hints are directional and non-evidence."],
        "prohibited_upgrades": ["Do not treat Scout snippets as citations."],
        "normalization_obligations": ["Keep effective year normalization at 2026."],
        "assumptions": [],
        "unresolved_ambiguities": [
            {
                "unresolved_id": "unresolved:jurisdiction",
                "summary": "Jurisdiction remains unresolved.",
            }
        ],
        "consumed_ambiguity_dimension_ids": list(CONSUMED_DIMENSION_IDS),
        "consumed_scout_hint_ids": list(CONSUMED_HINT_IDS),
        "amendment_candidates": [
            {
                "candidate_id": "candidate:revision-add-caveat",
                "operation_kind": operation_kind,
                "component_id": COMPONENT_ID,
                "caveat": "Jurisdiction remains unresolved; Scout hints are not evidence.",
                "summary": "Add a monotonic non-evidence caveat.",
            }
        ],
        "closed_surface_flags": dict(FALSE_FLAGS),
        "confidence_posture": "directional",
        "revision_posture": "proposal_only",
    }
    if extra:
        payload.update(extra)
    return payload


def _kernel() -> RunKernel:
    return RunKernel.start(run_id=RUN_ID, request_id=REQUEST_ID)


def _planner_input(kernel: RunKernel) -> SearchPlannerInput:
    return SearchPlannerInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        user_query_text=QUERY,
        requested_mode="balanced",
        safe_context={"source_policy": "official-current"},
        parent_initial_contract_ref=planner_contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=planner_contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
    )


def _produce_planner(kernel: RunKernel) -> Mapping[str, Any]:
    planner_input = _planner_input(kernel)
    action = kernel.authorize_search_planner_production(
        user_query_digest=planner_input.user_query_digest,
        planner_schema_version=SEARCH_PLANNER_SCHEMA_VERSION,
    )
    result = execute_search_planner_action(
        action=action,
        planner_input=planner_input,
        adapter=DeterministicPlannerAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_PRODUCED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)
    return kernel.state.search_planner_proposal_projection["question_meaning_record"]


def _accept_planner_qmr(kernel: RunKernel, qmr_payload: Mapping[str, Any]) -> None:
    action = kernel.authorize_initial_answer_contract_acceptance(
        parent_question_meaning_record_id=str(qmr_payload["record_id"]),
        parent_proposal_digest=str(qmr_payload["record_digest"]),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED,
        status=RunStageStatus.COMPLETED,
        payload={"question_meaning_record": dict(qmr_payload)},
    )
    kernel.reduce(observation)


def _scout_input(kernel: RunKernel) -> ScoutDisambiguationInput:
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    component = qmr["answer_components"][0]
    dims = _scout_dimensions()
    return ScoutDisambiguationInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            kernel.state.search_planner_proposal_state
        ),
        parent_initial_contract_ref=contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
        component_id=component["component_id"],
        answer_component_ref={
            "component_id": component["component_id"],
            "component_revision": component["component_revision"],
            "component_digest": component["component_digest"],
            "user_facing_label": component["user_facing_label"],
        },
        ambiguity_dimensions=dims,
        candidate_queries=[
            {
                "query_id": "scout-query:official",
                "safe_query_text": "Example Permit official 2026 threshold",
                "query_kind": "official_domain_probe",
                "priority": 1,
                "related_dimension_ids": ["dim:entity"],
            }
        ],
        safe_context={"adapter_policy": "fake-injected-only"},
    )


def _reduce_scout(kernel: RunKernel) -> None:
    scout_input = _scout_input(kernel)
    action = kernel.authorize_scout_disambiguation(
        component_id=scout_input.component_id,
        ambiguity_dimension_ids=[
            item["dimension_id"] for item in scout_input.ambiguity_dimensions
        ],
    )
    result = execute_scout_disambiguation_action(
        action=action,
        scout_input=scout_input,
        adapter=FakeScoutAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SCOUT_DISAMBIGUATION_REPORTED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)


def _revision_input(kernel: RunKernel) -> SearchPlannerRevisionInput:
    qmr = kernel.state.search_planner_proposal_projection["question_meaning_record"]
    return SearchPlannerRevisionInput(
        run_id=RUN_ID,
        request_id=REQUEST_ID,
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            kernel.state.search_planner_proposal_state
        ),
        parent_scout_disambiguation_report_ref=scout_ref_from_scout_report_state(
            kernel.state.scout_disambiguation_report_state
        ),
        parent_initial_contract_ref=contract_ref_from_contract(
            kernel.state.initial_answer_contract,
            source="initial_answer_contract",
        ),
        parent_current_contract_ref=contract_ref_from_contract(
            kernel.state.current_answer_contract,
            source="current_answer_contract",
        ),
        component_id=COMPONENT_ID,
        consumed_ambiguity_dimension_ids=CONSUMED_DIMENSION_IDS,
        consumed_scout_hint_ids=CONSUMED_HINT_IDS,
        safe_revision_context={
            "parent_question_meaning_record": qmr,
            "answer_component_ref": qmr["answer_components"][0],
            "user_query_ref": kernel.state.search_planner_proposal_projection[
                "user_query_ref"
            ],
            "scout_report_projection": kernel.state.scout_disambiguation_report_projection,
        },
    )


def _prepare_kernel() -> RunKernel:
    kernel = _kernel()
    qmr = _produce_planner(kernel)
    _accept_planner_qmr(kernel, qmr)
    _reduce_scout(kernel)
    return kernel


def _authorize_revision(kernel: RunKernel, revision_input: SearchPlannerRevisionInput):
    return kernel.authorize_search_planner_revision(
        component_id=revision_input.component_id,
        consumed_ambiguity_dimension_ids=revision_input.consumed_ambiguity_dimension_ids,
        consumed_scout_hint_ids=revision_input.consumed_scout_hint_ids,
    )


def _reduce_revision(
    kernel: RunKernel,
    *,
    adapter: FakeRevisionAdapter | None = None,
    revision_input: SearchPlannerRevisionInput | None = None,
) -> None:
    input_ = revision_input or _revision_input(kernel)
    action = _authorize_revision(kernel, input_)
    result = execute_search_planner_revision_action(
        action=action,
        revision_input=input_,
        adapter=adapter or FakeRevisionAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)


def _revision_lineage_inputs(kernel: RunKernel) -> dict[str, Any]:
    revision = kernel.state.search_planner_revision_projection
    planner_ref = revision["parent_search_planner_proposal_ref"]
    scout_ref = revision["parent_scout_disambiguation_report_ref"]
    return {
        "search_planner_revision_lineage_required": True,
        "amendment_origin": "search_planner_revision",
        "planner_revision_id": revision["revision_id"],
        "parent_search_planner_proposal_id": planner_ref["proposal_id"],
        "parent_search_planner_proposal_digest": planner_ref["proposal_digest"],
        "parent_question_meaning_record_id": planner_ref[
            "question_meaning_record_id"
        ],
        "parent_question_meaning_record_digest": planner_ref[
            "question_meaning_record_digest"
        ],
        "parent_scout_disambiguation_report_id": scout_ref["report_id"],
        "parent_scout_disambiguation_report_digest": scout_ref["report_digest"],
        "component_id": revision["component_id"],
        "consumed_ambiguity_dimension_ids": revision[
            "consumed_ambiguity_dimension_ids"
        ],
        "consumed_scout_hint_ids": revision["consumed_scout_hint_ids"],
    }


def _admit_revision_candidate(kernel: RunKernel) -> Mapping[str, Any]:
    candidate = kernel.state.search_planner_revision_projection["amendment_candidates"][0]
    record = candidate["contract_amendment_record"]
    _admit_record_with_inputs(kernel, record, inputs=_revision_lineage_inputs(kernel))
    return record


def _admit_record_with_inputs(
    kernel: RunKernel,
    record: Mapping[str, Any],
    *,
    inputs: Mapping[str, Any] | None = None,
) -> None:
    action = kernel.authorize_contract_amendment_admission(
        amendment_record_id=record["amendment_record_id"],
        amendment_record_digest=record["record_digest"],
        inputs=inputs,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_ADMITTED,
        status=RunStageStatus.COMPLETED,
        payload={"contract_amendment_record": record},
    )
    kernel.reduce(observation)


def _apply_admitted_revision_candidate(kernel: RunKernel, record: Mapping[str, Any]) -> None:
    admission = kernel.state.contract_amendment_admission_projection
    action = kernel.authorize_contract_amendment_application(
        amendment_record_id=record["amendment_record_id"],
        amendment_record_digest=record["record_digest"],
        admission_digest=admission["admission_digest"],
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.CONTRACT_AMENDMENT_APPLIED,
        status=RunStageStatus.COMPLETED,
        payload={},
    )
    kernel.reduce(observation)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(_text(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_search_planner_revision_requires_adapter_and_fails_closed_without_one() -> None:
    kernel = _prepare_kernel()
    revision_input = _revision_input(kernel)
    action = _authorize_revision(kernel, revision_input)

    with pytest.raises(SearchPlannerRevisionRuntimeError, match="injected adapter"):
        execute_search_planner_revision_action(
            action=action,
            revision_input=revision_input,
        )

    assert kernel.state.search_planner_revision_state == {}
    assert kernel.state.search_planner_revision_projection == {}
    assert kernel.state.search_planner_revision_history == []


def test_search_planner_revision_reduces_to_run_kernel_state_projection_history() -> None:
    kernel = _prepare_kernel()
    adapter = FakeRevisionAdapter()

    _reduce_revision(kernel, adapter=adapter)

    state = kernel.state.search_planner_revision_state
    projection = kernel.state.search_planner_revision_projection
    assert adapter.calls
    assert state["owner"] == SEARCH_PLANNER_REVISION_OWNER
    assert state["schema_version"] == SEARCH_PLANNER_REVISION_PROPOSAL_SCHEMA_VERSION
    assert state["run_id"] == RUN_ID
    assert state["request_id"] == REQUEST_ID
    assert state["authorized_action_id"]
    assert state["revision_digest"]
    assert state["parent_search_planner_proposal_ref"]["proposal_digest"]
    assert state["parent_scout_disambiguation_report_ref"]["report_digest"]
    assert state["component_id"] == COMPONENT_ID
    assert state["consumed_ambiguity_dimension_ids"] == CONSUMED_DIMENSION_IDS
    assert state["consumed_scout_hint_ids"] == CONSUMED_HINT_IDS
    for key, expected in FALSE_FLAGS.items():
        assert state[key] is expected
        assert projection[key] is expected
    assert kernel.state.search_planner_revision_history[-1] == projection
    assert kernel.state.projections[SEARCH_PLANNER_REVISION_STAGE] == projection


def test_revision_binds_to_parent_planner_qmr_scout_and_contracts() -> None:
    for field, value, match in (
        ("proposal_digest", "stale-planner", "stale parent planner"),
        (
            "question_meaning_record_digest",
            "stale-qmr",
            "stale parent planner",
        ),
    ):
        kernel = _prepare_kernel()
        revision_input = _revision_input(kernel)
        action = _authorize_revision(kernel, revision_input)
        tampered = revision_input.to_adapter_payload()
        tampered["parent_search_planner_proposal_ref"][field] = value
        payload = build_search_planner_revision_observation_payload(
            adapter_result=_revision_result(),
            revision_input=tampered,
            authorized_action_id=action.action_id,
        )
        observation = Observation.from_action(
            action,
            observation_type=ObservationType.SEARCH_PLANNER_REVISED,
            status=RunStageStatus.COMPLETED,
            payload=payload,
        )
        with pytest.raises(RunKernelTransitionError, match=match):
            kernel.reduce(observation)

    kernel = _prepare_kernel()
    revision_input = _revision_input(kernel)
    action = _authorize_revision(kernel, revision_input)
    tampered = revision_input.to_adapter_payload()
    tampered["parent_scout_disambiguation_report_ref"]["report_digest"] = "stale"
    payload = build_search_planner_revision_observation_payload(
        adapter_result=_revision_result(),
        revision_input=tampered,
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    with pytest.raises(RunKernelTransitionError, match="stale Scout report"):
        kernel.reduce(observation)

    kernel = _prepare_kernel()
    revision_input = _revision_input(kernel)
    action = _authorize_revision(kernel, revision_input)
    tampered = revision_input.to_adapter_payload()
    tampered["parent_initial_contract_ref"]["contract_digest"] = "stale"
    payload = build_search_planner_revision_observation_payload(
        adapter_result=_revision_result(),
        revision_input=tampered,
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    with pytest.raises(RunKernelTransitionError, match="stale parent digest"):
        kernel.reduce(observation)

    current_kernel = _prepare_kernel()
    _reduce_revision(current_kernel)
    record = _admit_revision_candidate(current_kernel)
    _apply_admitted_revision_candidate(current_kernel, record)
    revision_input = _revision_input(current_kernel)
    action = _authorize_revision(current_kernel, revision_input)
    tampered = revision_input.to_adapter_payload()
    tampered["parent_current_contract_ref"]["contract_digest"] = "stale-current"
    payload = build_search_planner_revision_observation_payload(
        adapter_result=_revision_result(),
        revision_input=tampered,
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    with pytest.raises(RunKernelTransitionError, match="stale parent digest"):
        current_kernel.reduce(observation)


def test_revision_rejects_stale_or_unrelated_scout_report() -> None:
    source_kernel = _prepare_kernel()
    target_kernel = _prepare_kernel()
    revision_input = _revision_input(target_kernel)
    action = _authorize_revision(target_kernel, revision_input)
    unrelated = revision_input.to_adapter_payload()
    unrelated["parent_scout_disambiguation_report_ref"] = scout_ref_from_scout_report_state(
        source_kernel.state.scout_disambiguation_report_state
    )
    unrelated["parent_scout_disambiguation_report_ref"]["report_digest"] = (
        "unrelated-scout"
    )
    payload = build_search_planner_revision_observation_payload(
        adapter_result=_revision_result(),
        revision_input=unrelated,
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )

    with pytest.raises(RunKernelTransitionError, match="stale Scout report"):
        target_kernel.reduce(observation)


def test_revision_rejects_duplicate_context() -> None:
    kernel = _prepare_kernel()
    revision_input = _revision_input(kernel)
    _reduce_revision(kernel, revision_input=revision_input)

    action = _authorize_revision(kernel, revision_input)
    result = execute_search_planner_revision_action(
        action=action,
        revision_input=revision_input,
        adapter=FakeRevisionAdapter(),
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_PLANNER_REVISED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )

    with pytest.raises(RunKernelTransitionError, match="duplicate search planner revision"):
        kernel.reduce(observation)


def test_revision_consumes_scout_hints_as_non_evidence() -> None:
    kernel = _prepare_kernel()
    evidence_before = kernel.state.evidence_ledger.to_projection().to_dict()
    citation_before = deepcopy(kernel.state.followup_citation_eligibility_history)

    _reduce_revision(kernel)

    state = kernel.state.search_planner_revision_state
    assert state["consumed_scout_hint_ids"] == CONSUMED_HINT_IDS
    assert state["scout_hints_are_evidence"] is False
    assert state["evidence_admitted"] is False
    assert state["citation_eligible"] is False
    assert state["source_obligation_satisfied"] is False
    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    assert kernel.state.followup_citation_eligibility_history == citation_before


def test_revision_emits_qmr_compatible_or_revision_compatible_payload() -> None:
    kernel = _prepare_kernel()
    planner_before = deepcopy(kernel.state.search_planner_proposal_state)

    _reduce_revision(kernel)

    revision = kernel.state.search_planner_revision_projection
    assert revision["revised_question_meaning_summary"]
    assert revision["semantic_slot_updates"][0]["slot_id"] == "slot:program"
    assert revision["answer_component_updates"][0]["component_id"] == COMPONENT_ID
    assert revision["component_search_requirement_updates"][0]["must_not_execute"] is True
    assert kernel.state.search_planner_proposal_state == planner_before


def test_revision_emits_passive_add_caveat_amendment_candidate() -> None:
    kernel = _prepare_kernel()

    _reduce_revision(kernel)

    candidate = kernel.state.search_planner_revision_projection["amendment_candidates"][0]
    record = candidate["contract_amendment_record"]
    assert candidate["operation_kind"] == "add_caveat"
    assert candidate["passive"] is True
    assert candidate["proposal_only"] is True
    assert record["passive"] is True
    assert record["canonical_state"] is False
    assert record["contract_mutation_applied"] is False
    assert candidate["evidence_admitted"] is False
    assert candidate["citation_eligible"] is False
    assert candidate["source_obligation_satisfied"] is False
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.contract_amendment_application_history == []
    assert kernel.state.current_answer_contract == {}


def test_revision_amendment_admission_requires_lineage_bindings_when_record_declares_revision_lineage() -> None:
    kernel = _prepare_kernel()
    _reduce_revision(kernel)
    record = kernel.state.search_planner_revision_projection["amendment_candidates"][0][
        "contract_amendment_record"
    ]

    with pytest.raises(
        RunKernelTransitionError,
        match="search planner revision admission binding requires planner_revision_id",
    ):
        _admit_record_with_inputs(kernel, record)

    assert kernel.state.current_answer_contract == {}
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.contract_amendment_admission_projection == {}


def test_revision_amendment_admission_accepts_when_full_lineage_bindings_match() -> None:
    kernel = _prepare_kernel()
    _reduce_revision(kernel)

    record = _admit_revision_candidate(kernel)
    projection = kernel.state.contract_amendment_admission_projection

    assert projection["amendment_record_id"] == record["amendment_record_id"]
    assert projection["search_planner_revision_lineage"]["origin"] == (
        "search_planner_revision"
    )
    assert projection["contract_mutation_applied"] is False
    assert kernel.state.current_answer_contract == {}
    assert len(kernel.state.contract_amendment_admission_history) == 1


def test_revision_amendment_admission_rejects_stale_revision_or_scout_lineage() -> None:
    kernel = _prepare_kernel()
    _reduce_revision(kernel)
    record = kernel.state.search_planner_revision_projection["amendment_candidates"][0][
        "contract_amendment_record"
    ]
    inputs = _revision_lineage_inputs(kernel)
    inputs["parent_scout_disambiguation_report_digest"] = "stale-scout"

    with pytest.raises(
        RunKernelTransitionError,
        match="parent Scout lineage does not match",
    ):
        _admit_record_with_inputs(kernel, record, inputs=inputs)

    assert kernel.state.current_answer_contract == {}
    assert kernel.state.contract_amendment_admission_history == []
    assert kernel.state.contract_amendment_admission_projection == {}


def test_revision_amendment_candidate_admission_and_application_updates_current_contract() -> None:
    kernel = _prepare_kernel()
    initial_before = deepcopy(kernel.state.initial_answer_contract)

    _reduce_revision(kernel)
    after_revision_current = deepcopy(kernel.state.current_answer_contract)
    record = _admit_revision_candidate(kernel)
    after_admission_current = deepcopy(kernel.state.current_answer_contract)
    _apply_admitted_revision_candidate(kernel, record)

    current = kernel.state.current_answer_contract
    assert after_revision_current == {}
    assert after_admission_current == {}
    assert current
    assert current["accepted_contract_digest"] != initial_before["accepted_contract_digest"]
    assert current["previous_contract_digest"] == initial_before["accepted_contract_digest"]
    assert kernel.state.initial_answer_contract == initial_before
    assert "Jurisdiction remains unresolved; Scout hints are not evidence." in current[
        "mandatory_caveats"
    ]
    component = current["accepted_answer_component_refs"][0]
    assert "Jurisdiction remains unresolved; Scout hints are not evidence." in component[
        "mandatory_caveats"
    ]
    assert kernel.state.contract_amendment_admission_projection[
        "contract_mutation_applied"
    ] is False
    assert kernel.state.contract_amendment_application_projection[
        "contract_mutation_applied"
    ] is True
    applied_ref = current["applied_amendment_refs"][0]
    assert applied_ref["search_planner_revision_lineage"]["origin"] == (
        "search_planner_revision"
    )
    assert applied_ref["applied_operation_kinds"] == ["add_caveat"]


@pytest.mark.parametrize("operation_kind", ["resolve_slot", "mark_requirement_satisfied"])
def test_revision_rejects_resolve_slot_or_requirement_satisfaction_from_scout_hints(
    operation_kind: str,
) -> None:
    kernel = _prepare_kernel()
    revision_input = _revision_input(kernel)
    action = _authorize_revision(kernel, revision_input)

    with pytest.raises(SearchPlannerRevisionRuntimeError):
        execute_search_planner_revision_action(
            action=action,
            revision_input=revision_input,
            adapter=FakeRevisionAdapter(_revision_result(operation_kind=operation_kind)),
        )

    assert kernel.state.search_planner_revision_state == {}


def test_revision_rejects_closed_authority_or_raw_payload_fields() -> None:
    kernel = _prepare_kernel()
    unsafe = _revision_result(
        extra={
            "evidence_ledger_admission": {"claim": "not allowed"},
            "citation_eligible": True,
            "source_obligation_satisfied": True,
            "current_answer_contract": {"mutated": True},
            "final_answer_packet": {"created": True},
            "author_input": {"created": True},
            "raw_provider_payload": {"private": True},
            "raw_search_response": {"private": True},
            "raw_model_response": "private",
            "raw_prompt": "private",
        }
    )

    with pytest.raises(SearchPlannerRevisionRuntimeError):
        _reduce_revision(kernel, adapter=FakeRevisionAdapter(unsafe))

    assert kernel.state.search_planner_revision_state == {}
    assert kernel.state.search_planner_revision_projection == {}
    assert kernel.state.search_planner_revision_history == []


def test_revision_does_not_activate_search_executor_or_retrieval() -> None:
    kernel = _prepare_kernel()
    evidence_before = kernel.state.evidence_ledger.to_projection().to_dict()

    _reduce_revision(kernel)

    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_work_plan_projection == {}
    assert kernel.state.offline_search_executor_bridge_projection == {}
    assert kernel.state.offline_search_executor_bridge_history == []
    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    revision = kernel.state.search_planner_revision_projection
    for key in (
        "fetch_read_retrieval_behavior_changed",
        "search_executor_runtime_activated",
        "search_work_plan_constructed",
        "evidence_admitted",
        "citation_eligible",
        "source_obligation_satisfied",
    ):
        assert revision[key] is False


def test_static_closed_surface_guard_for_search_planner_revision() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.scout",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.search_executor",
        "core.evidence_ledger_admission_runtime",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.citations",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    for path in (REVISION_RUNTIME, REVISION_ADAPTER, REVISION_PROMPT):
        assert _imports(path).isdisjoint(forbidden_imports), path
        source = _text(path)
        for token in (
            "SERPER_API_KEY",
            "ask_model(",
            "run_scout(",
            "SearchExecutor(",
            "fetch_linkup_precision_block",
            "execute_author_action(",
            "build_citation",
            "requests.",
            "httpx.",
            "openai.",
        ):
            assert token not in source, (path, token)
    kernel_text = _text(RUN_KERNEL)
    assert "SEARCH_PLANNER_REVISE" in kernel_text
    assert "SEARCH_PLANNER_REVISED" in kernel_text

    pipeline_source = _text(PIPELINE)
    assert "revision_adapter=revision_adapter" in pipeline_source
    assert "revision_adapter = deps.search_planner_revision_adapter" in pipeline_source
    assert 'getattr(deps, "search_planner_revision_adapter", None)' not in pipeline_source
    assert "execute_initial_query_strategy_convergence(" in pipeline_source


def test_docs_record_revision_authority_split() -> None:
    required = (
        "SEARCHOS-QUERY-STRATEGY-AND-RECON-CONVERGENCE-01",
        "SearchPlannerRevision query-direction-only changes cannot mutate the AnswerContract",
        "contractual revision reaches planning only after existing amendment admission and application",
        "Scout reports remain non-evidence",
        "No live provider, model, search, recon, fetch/read, or retrieval call was made",
    )
    forbidden = (
        "planner revision directly mutates contracts",
        "Scout hints are evidence",
        "Scout hints satisfy source obligations",
        "Scout hints create citations",
        "planner revision executes SearchExecutor",
        "planner revision fetches or reads pages",
        "planner revision bypasses amendment admission",
    )
    for path in DOCS:
        text = " ".join(_text(path).split())
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
