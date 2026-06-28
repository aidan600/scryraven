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
from tests.test_ag_search_planner_revision_01 import (
    COMPONENT_ID,
    CONSUMED_HINT_IDS,
    _accept_planner_qmr,
    _admit_revision_candidate,
    _apply_admitted_revision_candidate,
    _kernel,
    _prepare_kernel,
    _produce_planner,
    _reduce_revision,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULE = ROOT / "core" / "search_executor_handoff_runtime.py"
RUN_KERNEL = ROOT / "core" / "run_kernel.py"
PIPELINE = ROOT / "core" / "pipeline_orchestrator.py"
DOCS = (
    ROOT / "docs" / "architecture" / "RUN_CONTRACT_SEMANTIC_LOOP.md",
    ROOT / "docs" / "architecture" / "SCRYRAVEN_CURRENT_STATE.md",
    ROOT / "docs" / "codex" / "CODEX_GUIDANCE_MAP.md",
    ROOT / "docs" / "codex" / "RUNAUTHORITY_IMPLEMENTATION_GUIDE.md",
)

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


def _initial_only_kernel() -> RunKernel:
    kernel = _kernel()
    qmr = _produce_planner(kernel)
    _accept_planner_qmr(kernel, qmr)
    return kernel


def _current_contract_kernel() -> RunKernel:
    kernel = _prepare_kernel()
    _reduce_revision(kernel)
    record = _admit_revision_candidate(kernel)
    _apply_admitted_revision_candidate(kernel, record)
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
        contract_parent_kind=(
            "current_answer_contract"
            if current_ref
            else "initial_answer_contract_fallback"
        ),
        parent_search_planner_proposal_ref=planner_ref_from_search_planner_state(
            kernel.state.search_planner_proposal_state
        ),
        parent_search_planner_revision_ref=revision_ref_from_revision_state(
            kernel.state.search_planner_revision_state
        ),
        parent_scout_disambiguation_report_ref=(
            scout_ref_from_scout_report_state(
                kernel.state.scout_disambiguation_report_state
            )
            if direction_refs
            else {}
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
    assert state["parent_current_contract_ref"]["contract_digest"] == (
        kernel.state.current_answer_contract["accepted_contract_digest"]
    )
    assert state["parent_initial_contract_ref"]["contract_digest"] == (
        kernel.state.initial_answer_contract["accepted_contract_digest"]
    )
    assert "Jurisdiction remains unresolved; Scout hints are not evidence." in state[
        "required_caveats"
    ]


def test_search_executor_handoff_explicit_initial_fallback_when_no_current_contract() -> None:
    kernel = _initial_only_kernel()

    _reduce_handoff(kernel, handoff_input=_handoff_input(kernel, include_direction=False))

    state = kernel.state.search_executor_handoff_state
    assert state["contract_parent_kind"] == "initial_answer_contract_fallback"
    assert state["parent_current_contract_ref"] == {}
    assert state["parent_initial_contract_ref"]["contract_digest"] == (
        kernel.state.initial_answer_contract["accepted_contract_digest"]
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


def test_search_executor_handoff_binds_to_planner_revision_scout_and_contracts() -> None:
    def assert_reject(mutator, match: str) -> None:
        kernel = _current_contract_kernel()
        input_ = _handoff_input(kernel)
        observation, _payload = _payload_from_input(kernel, input_, mutator)
        with pytest.raises(RunKernelTransitionError, match=match):
            kernel.reduce(observation)

    assert_reject(
        lambda payload: payload["parent_current_contract_ref"].update(
            {"contract_digest": "stale-current"}
        ),
        "stale parent digest",
    )
    assert_reject(
        lambda payload: payload["parent_initial_contract_ref"].update(
            {"contract_digest": "stale-initial"}
        ),
        "stale parent digest",
    )
    assert_reject(
        lambda payload: payload["parent_search_planner_proposal_ref"].update(
            {"proposal_digest": "stale-planner"}
        ),
        "stale parent planner",
    )
    assert_reject(
        lambda payload: payload["parent_search_planner_proposal_ref"].update(
            {"question_meaning_record_digest": "stale-qmr"}
        ),
        "stale parent planner",
    )
    assert_reject(
        lambda payload: payload["parent_search_planner_revision_ref"].update(
            {"revision_digest": "stale-revision"}
        ),
        "stale planner revision",
    )
    assert_reject(
        lambda payload: payload["parent_scout_disambiguation_report_ref"].update(
            {"report_digest": "stale-scout"}
        ),
        "stale Scout report",
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


def test_scout_direction_refs_remain_non_evidence() -> None:
    kernel = _current_contract_kernel()
    evidence_before = kernel.state.evidence_ledger.to_projection().to_dict()
    citation_before = deepcopy(kernel.state.followup_citation_eligibility_history)

    _reduce_handoff(kernel)

    state = kernel.state.search_executor_handoff_state
    assert state["scout_direction_hint_refs"]
    assert state["non_evidence_direction_refs"]
    assert state["scout_direction_hint_refs"][0]["hint_id"] in CONSUMED_HINT_IDS
    for ref in state["non_evidence_direction_refs"]:
        assert ref["role"] == "search_direction_only"
        assert ref["evidence_admitted"] is False
        assert ref["citation_eligible"] is False
        assert ref["source_obligation_satisfied"] is False
        assert ref["fetch_read_retrieval_executed"] is False
    assert kernel.state.evidence_ledger.to_projection().to_dict() == evidence_before
    assert kernel.state.followup_citation_eligibility_history == citation_before


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
            "serper_api_key": "secret",
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
        "PR #329 / AG-SEARCH-PLANNER-REVISION-01",
        "AG-SEARCH-EXECUTOR-HANDOFF-01",
        "handoff consumes current_answer_contract when present",
        "Scout/revision material is search direction only",
        "handoff creates search task records",
        "search work packet",
        "no live search/provider/fetch/read/retrieval calls were run",
        "no EvidenceLedger/citations/source-obligation satisfaction",
        "post-merge next gate is AG-LIVE-XAXIS-VALIDATION-01",
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
        text = _text(path)
        for needle in required:
            assert needle in text, (path, needle)
        for needle in forbidden:
            assert needle not in text, (path, needle)
