from __future__ import annotations

import ast
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pytest

from core.run_kernel import (
    SEARCH_EXECUTOR_HANDOFF_STAGE,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
    RunStageStatus,
)
from core.search_executor_handoff_runtime import (
    SEARCH_EXECUTOR_HANDOFF_OWNER,
    SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION,
    SearchExecutorHandoffInput,
    SearchExecutorHandoffRuntimeError,
    build_search_executor_handoff_observation_payload,
    contract_ref_from_contract,
    execute_search_executor_handoff_action,
    planner_ref_from_search_planner_state,
    revision_ref_from_revision_state,
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
from tests.helpers.canonical_answer_contract_fixture import (
    apply_nonmaterial_current_contract_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "search_executor_handoff_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
)
RUN_ID = "run:ag-search-executor-handoff-01"
REQUEST_ID = "request:ag-search-executor-handoff-01"
QUERY = "What is the current official Example Permit threshold in 2026?"
COMPONENT_ID = "component:official-threshold"

FALSE_FLAGS = {
    "provider_calls_executed": False,
    "live_search_executed": False,
    "fetch_read_retrieval_executed": False,
    "retrieval_executed": False,
    "search_provider_called": False,
    "evidence_admitted": False,
    "evidence_ledger_custody_created": False,
    "citation_eligible": False,
    "source_obligation_satisfied": False,
    "sufficiency_decided": False,
    "final_answer_packet_created": False,
    "author_input_created": False,
    "live_validation_run": False,
    "search_executor_runtime_activated": False,
    "search_work_plan_activated": False,
    "contract_mutation_applied": False,
    "current_answer_contract_mutated": False,
    "initial_answer_contract_mutated": False,
    "raw_provider_payload_retained": False,
    "raw_search_response_retained": False,
    "raw_prompt_retained": False,
    "raw_model_response_retained": False,
}


class DeterministicPlannerAdapter:
    def produce(self, planner_input: Mapping[str, Any]) -> Mapping[str, Any]:
        return _planner_result()


def _planner_result() -> dict[str, Any]:
    return {
        "question_meaning_summary": (
            "Determine the official current threshold while preserving material identity and jurisdiction ambiguity."
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
                    "What is the official current filing threshold for the requested program?"
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


def _initial_only_kernel() -> RunKernel:
    kernel = _kernel()
    qmr = _produce_planner(kernel)
    _accept_planner_qmr(kernel, qmr)
    return kernel


def _current_contract_kernel() -> RunKernel:
    kernel = _initial_only_kernel()
    apply_nonmaterial_current_contract_fixture(
        kernel,
        fixture_id="ag-search-executor-handoff",
    )
    return kernel


def _active_contract(kernel: RunKernel) -> Mapping[str, Any]:
    return kernel.state.current_answer_contract or kernel.state.initial_answer_contract


def _source_refs_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for component in contract.get("accepted_answer_component_refs", []) or []:
        component_id = component["component_id"]
        for candidate_id in component.get("source_obligation_candidate_ids", []) or []:
            refs.append(
                {
                    "candidate_id": candidate_id,
                    "component_candidate_ids": [component_id],
                    "obligation_kind": "source_support",
                    "strictness": "required",
                }
            )
    return refs


def _direction_refs(kernel: RunKernel) -> list[dict[str, Any]]:
    report = kernel.state.scout_disambiguation_report_state
    consumed = set(kernel.state.search_planner_revision_state.get("consumed_scout_hint_ids", []))
    refs: list[dict[str, Any]] = []
    for hint in report.get("scout_result_hints", []) or []:
        if hint.get("hint_id") not in consumed:
            continue
        refs.append(
            {
                "direction_ref_id": f"direction:{hint['hint_id']}",
                "source_report_id": report["report_id"],
                "hint_id": hint["hint_id"],
                "hint_kind": hint.get("hint_kind"),
                "title": hint.get("title"),
                "domain": hint.get("domain"),
                "link": hint.get("link"),
            }
        )
    return refs


def _caveats(kernel: RunKernel) -> list[str]:
    contract = _active_contract(kernel)
    caveats = list(contract.get("mandatory_caveats", []) or [])
    for component in contract.get("accepted_answer_component_refs", []) or []:
        for caveat in component.get("mandatory_caveats", []) or []:
            if caveat not in caveats:
                caveats.append(caveat)
    for caveat in kernel.state.search_planner_revision_state.get("mandatory_caveats", []) or []:
        if caveat not in caveats:
            caveats.append(caveat)
    return caveats


def _prohibited_upgrades(kernel: RunKernel) -> list[str]:
    contract = _active_contract(kernel)
    upgrades = list(contract.get("prohibited_upgrades", []) or [])
    for component in contract.get("accepted_answer_component_refs", []) or []:
        for upgrade in component.get("prohibited_upgrades", []) or []:
            if upgrade not in upgrades:
                upgrades.append(upgrade)
    for upgrade in kernel.state.search_planner_revision_state.get("prohibited_upgrades", []) or []:
        if upgrade not in upgrades:
            upgrades.append(upgrade)
    return upgrades


def _handoff_input(
    kernel: RunKernel,
    *,
    include_direction: bool = True,
) -> SearchExecutorHandoffInput:
    contract = _active_contract(kernel)
    current_ref = contract_ref_from_contract(
        kernel.state.current_answer_contract,
        source="current_answer_contract",
    )
    initial_ref = contract_ref_from_contract(
        kernel.state.initial_answer_contract,
        source="initial_answer_contract",
    )
    direction_refs = _direction_refs(kernel) if include_direction else []
    return SearchExecutorHandoffInput(
        run_id=kernel.state.run_id,
        request_id=kernel.state.request_id,
        parent_current_contract_ref=current_ref,
        parent_initial_contract_ref=initial_ref,
        contract_parent_kind=("current_answer_contract" if current_ref else "initial_answer_contract_fallback"),
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            kernel.state.search_planner_proposal_state
        ),
        parent_search_planner_revision_ref=revision_ref_from_revision_state(kernel.state.search_planner_revision_state),
        parent_scout_disambiguation_report_ref=(
            scout_ref_from_scout_report_state(kernel.state.scout_disambiguation_report_state) if direction_refs else {}
        ),
        answer_component_refs=contract.get("accepted_answer_component_refs", []),
        source_obligation_candidate_refs=_source_refs_from_contract(contract),
        component_search_requirements=kernel.state.search_planner_proposal_state.get(
            "component_search_requirements",
            [],
        ),
        revision_search_requirement_updates=kernel.state.search_planner_revision_state.get(
            "component_search_requirement_updates",
            [],
        ),
        source_obligation_focus_updates=kernel.state.search_planner_revision_state.get(
            "source_obligation_focus_updates",
            [],
        ),
        scout_direction_hint_refs=direction_refs,
        non_evidence_direction_refs=direction_refs,
        required_caveats=_caveats(kernel),
        prohibited_upgrades=_prohibited_upgrades(kernel),
        query_budget={"max_search_tasks": 5, "max_results_per_task": 8},
        allowed_verticals=["search"],
        provider_preference_hint="serper",
    )


def _reduce_handoff(
    kernel: RunKernel,
    *,
    handoff_input: SearchExecutorHandoffInput | None = None,
) -> None:
    input_ = handoff_input or _handoff_input(kernel)
    action = kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=input_,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )
    kernel.reduce(observation)


def _payload_from_input(
    kernel: RunKernel,
    input_: SearchExecutorHandoffInput,
    mutator,
) -> tuple[Any, Mapping[str, Any]]:
    action = kernel.authorize_search_executor_handoff()
    payload_input = input_.to_payload()
    mutator(payload_input)
    payload = build_search_executor_handoff_observation_payload(
        handoff_input=payload_input,
        authorized_action_id=action.action_id,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
        status=RunStageStatus.COMPLETED,
        payload=payload,
    )
    return observation, payload


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


def test_search_executor_handoff_requires_current_or_initial_contract() -> None:
    kernel = _kernel()

    with pytest.raises(RunKernelTransitionError, match="initial answer contract"):
        kernel.authorize_search_executor_handoff()

    assert kernel.state.search_executor_handoff_state == {}
    assert kernel.state.search_executor_handoff_projection == {}
    assert kernel.state.search_executor_handoff_history == []


def test_search_executor_handoff_prefers_current_contract_when_present() -> None:
    kernel = _current_contract_kernel()

    _reduce_handoff(kernel)

    state = kernel.state.search_executor_handoff_state
    assert state["contract_parent_kind"] == "current_answer_contract"
    assert (
        state["parent_current_contract_ref"]["contract_digest"]
        == (kernel.state.current_answer_contract["accepted_contract_digest"])
    )
    assert (
        state["parent_initial_contract_ref"]["contract_digest"]
        == (kernel.state.initial_answer_contract["accepted_contract_digest"])
    )
    assert state["parent_search_planner_revision_ref"] == {}
    assert state["parent_scout_disambiguation_report_ref"] == {}
    assert state["required_caveats"] == ["Keep ambiguity visible until resolved."]


def test_search_executor_handoff_explicit_initial_fallback_when_no_current_contract() -> None:
    kernel = _initial_only_kernel()

    _reduce_handoff(kernel, handoff_input=_handoff_input(kernel, include_direction=False))

    state = kernel.state.search_executor_handoff_state
    assert state["contract_parent_kind"] == "initial_answer_contract_fallback"
    assert state["parent_current_contract_ref"] == {}
    assert (
        state["parent_initial_contract_ref"]["contract_digest"]
        == (kernel.state.initial_answer_contract["accepted_contract_digest"])
    )
    assert state["initial_answer_contract_fallback_explicit"] is True


def test_search_executor_handoff_reduces_to_run_kernel_state_projection_history() -> None:
    kernel = _current_contract_kernel()

    _reduce_handoff(kernel)

    state = kernel.state.search_executor_handoff_state
    projection = kernel.state.search_executor_handoff_projection
    assert state["owner"] == SEARCH_EXECUTOR_HANDOFF_OWNER
    assert state["schema_version"] == SEARCH_EXECUTOR_HANDOFF_SCHEMA_VERSION
    assert state["run_id"] == kernel.state.run_id
    assert state["request_id"] == kernel.state.request_id
    assert state["authorized_action_id"]
    assert state["handoff_digest"]
    assert state["search_executor_handoff_created"] is True
    assert state["search_work_packet_constructed"] is True
    assert state["not_live"] is True
    assert state["no_fetch_read_policy_active"] is True
    for key, expected in FALSE_FLAGS.items():
        assert state[key] is expected
        assert projection[key] is expected
    assert kernel.state.search_executor_handoff_history[-1] == projection
    assert kernel.state.projections[SEARCH_EXECUTOR_HANDOFF_STAGE] == projection


def test_search_executor_handoff_binds_to_planner_and_contracts() -> None:
    def assert_reject(mutator, match: str) -> None:
        kernel = _current_contract_kernel()
        input_ = _handoff_input(kernel)
        observation, _payload = _payload_from_input(kernel, input_, mutator)
        with pytest.raises(RunKernelTransitionError, match=match):
            kernel.reduce(observation)

    assert_reject(
        lambda payload: payload["parent_current_contract_ref"].update({"contract_digest": "stale-current"}),
        "stale parent digest",
    )
    assert_reject(
        lambda payload: payload["parent_initial_contract_ref"].update({"contract_digest": "stale-initial"}),
        "stale parent digest",
    )
    assert_reject(
        lambda payload: payload["parent_search_planner_proposal_ref"].update({"proposal_digest": "stale-planner"}),
        "stale parent planner",
    )
    assert_reject(
        lambda payload: payload["parent_search_planner_proposal_ref"].update(
            {"question_meaning_record_digest": "stale-qmr"}
        ),
        "stale parent planner",
    )


def test_search_executor_handoff_rejects_duplicate_context() -> None:
    kernel = _current_contract_kernel()
    input_ = _handoff_input(kernel)
    _reduce_handoff(kernel, handoff_input=input_)

    action = kernel.authorize_search_executor_handoff()
    result = execute_search_executor_handoff_action(
        action=action,
        handoff_input=input_,
    )
    observation = Observation.from_action(
        action,
        observation_type=ObservationType.SEARCH_EXECUTOR_HANDOFF_CREATED,
        status=RunStageStatus.COMPLETED,
        payload=result.observation_payload,
    )

    with pytest.raises(RunKernelTransitionError, match="duplicate SearchExecutor handoff"):
        kernel.reduce(observation)


def test_search_executor_handoff_constructs_query_intents_and_search_tasks() -> None:
    kernel = _current_contract_kernel()

    _reduce_handoff(kernel)

    state = kernel.state.search_executor_handoff_state
    intents = state["query_intent_records"]
    tasks = state["search_task_records"]
    assert intents
    assert tasks
    task = tasks[0]
    assert task["component_id"] == COMPONENT_ID
    assert task["source_obligation_candidate_ids"] == ["obligation:official-current"]
    assert task["search_requirement_id"]
    assert task["execution_status"] == "not_executed"
    assert task["not_live"] is True
    assert task["provider_preference_hint"] == "serper"
    assert state["query_budget"]["max_search_tasks"] == 5
    assert state["query_budget"]["max_results_per_task"] == 8
    assert task["max_results"] == 8


def test_search_executor_handoff_does_not_mutate_contracts() -> None:
    kernel = _current_contract_kernel()
    initial_before = deepcopy(kernel.state.initial_answer_contract)
    current_before = deepcopy(kernel.state.current_answer_contract)
    admission_before = deepcopy(kernel.state.contract_amendment_admission_history)
    application_before = deepcopy(kernel.state.contract_amendment_application_history)

    _reduce_handoff(kernel)

    assert kernel.state.initial_answer_contract == initial_before
    assert kernel.state.current_answer_contract == current_before
    assert kernel.state.contract_amendment_admission_history == admission_before
    assert kernel.state.contract_amendment_application_history == application_before


def test_search_executor_handoff_does_not_activate_provider_retrieval_evidence_citation_author_fap() -> None:
    kernel = _current_contract_kernel()
    evidence_before = kernel.state.evidence_ledger.to_projection().to_dict()
    citation_before = deepcopy(kernel.state.followup_citation_eligibility_history)
    sufficiency_before = deepcopy(kernel.state.sufficiency_judgment)
    final_packet_before = deepcopy(kernel.state.final_answer_packet)
    author_before = deepcopy(kernel.state.author_observation)

    _reduce_handoff(kernel)

    assert kernel.state.search_work_plan == {}
    assert kernel.state.search_work_plan_projection == {}
    assert kernel.state.offline_search_executor_bridge_projection == {}
    assert kernel.state.offline_search_executor_bridge_history == []
    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    assert kernel.state.followup_citation_eligibility_history == citation_before
    assert kernel.state.sufficiency_judgment == sufficiency_before
    assert kernel.state.final_answer_packet == final_packet_before
    assert kernel.state.author_observation == author_before
    for key, expected in FALSE_FLAGS.items():
        assert kernel.state.search_executor_handoff_state[key] is expected


def test_search_executor_handoff_rejects_closed_authority_or_raw_payload_fields() -> None:
    kernel = _current_contract_kernel()
    payload_input = _handoff_input(kernel).to_payload()
    payload_input.update(
        {
            "evidence_ledger_admission": {"claim": "not allowed"},
            "citation_eligible": True,
            "source_obligation_satisfied": True,
            "final_answer_packet": {"created": True},
            "author_input": {"created": True},
            "raw_provider_payload": {"private": True},
            "raw_search_response": {"private": True},
            "serper_api_key": "secret",  # pragma: allowlist secret
        }
    )

    with pytest.raises(SearchExecutorHandoffRuntimeError):
        build_search_executor_handoff_observation_payload(
            handoff_input=payload_input,
            authorized_action_id="action:test",
        )

    assert kernel.state.search_executor_handoff_state == {}
    assert kernel.state.search_executor_handoff_projection == {}
    assert kernel.state.search_executor_handoff_history == []


def test_static_closed_surface_guard_for_search_executor_handoff() -> None:
    forbidden_imports = {
        "core.run_kernel",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.evidence_ledger_admission_runtime",
        "core.author_execution_runtime",
        "core.final_answer_packet_runtime",
        "core.citations",
        "dotenv",
        "openai",
        "requests",
        "httpx",
    }
    assert _imports(RUNTIME_MODULE).isdisjoint(forbidden_imports)
    source = _text(RUNTIME_MODULE)
    for token in (
        "SERPER_API_KEY",
        "serper.dev",
        "requests.",
        "httpx.",
        "openai.",
        "SearchExecutor(",
        "fetch_linkup_precision_block",
        "execute_author_action(",
        "build_citation",
        "EvidenceLedger(",
    ):
        assert token not in source, token
    kernel_text = _text(RUN_KERNEL)
    assert "SEARCH_EXECUTOR_HANDOFF" in kernel_text
    assert "SEARCH_EXECUTOR_HANDOFF_CREATED" in kernel_text

    diff = subprocess.run(
        ["git", "diff", "--numstat", "--", str(PIPELINE.relative_to(ROOT))],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert diff.stdout.strip() == ""


def test_docs_use_merge_stable_search_executor_handoff_posture() -> None:
    required = (
        "PR #330 / AG-SEARCH-EXECUTOR-HANDOFF-01",
        "AG-SEARCH-EXECUTOR-HANDOFF-01",
        "handoff consumes current_answer_contract when present",
        "Scout/revision material is search direction only",
        "handoff creates search task records",
        "search work packet",
        "no live search/provider/fetch/read/retrieval calls were run",
        "no EvidenceLedger/citations/source-obligation satisfaction",
        "next implementation gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is AG-LIVE-XAXIS-VALIDATION-01A",
    )
    forbidden = (
        "handoff executes live search",
        "handoff fetches or reads pages",
        "handoff admits evidence",
        "handoff creates citations",
        "handoff satisfies source obligations",
        "handoff creates final answer packet",
        "partial-answer readiness is now next",
    )
    for path in DOCS:
        text = " ".join(_text(path).split())
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
