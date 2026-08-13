from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_evidence_intake_runtime import (
    AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE,
)
from core.followup_sufficiency_recheck_runtime import (
    FollowupSufficiencyPosture,
    evidence_ledger_projection_digest,
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.helpers.followup_fixture_spine import run_followup_through_execution
from tests.test_ag96i3m2_followup_evidence_intake_activation import (
    _execute_m2_intake,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i3n-m2-sufficiency-recheck"


def test_valid_m2_intake_authorizes_executes_and_reduces_recheck() -> None:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    _execute_m2_intake(kernel)
    before = _closed_surface_snapshot(kernel)

    action = kernel.authorize_followup_sufficiency_recheck()
    ledger_projection = kernel.state.evidence_ledger.to_projection().to_dict()
    intake = kernel.state.followup_evidence_intake_state

    assert action.stage == FOLLOWUP_SUFFICIENCY_RECHECK_STAGE
    assert action.inputs["intake_id"] == intake["intake_id"]
    assert action.inputs["followup_evidence_intake_id"] == intake["intake_id"]
    assert action.inputs["followup_evidence_intake_observation_id"] == (intake["observation_id"])
    assert action.inputs["execution_id"] == intake["execution_id"]
    assert action.inputs["followup_execution_id"] == intake["followup_execution_id"]
    assert action.inputs["followup_execution_observation_id"] == (intake["followup_execution_observation_id"])
    assert action.inputs["followup_authorization_consumption_id"] == (intake["followup_authorization_consumption_id"])
    assert action.inputs["sealed_candidate_id"] == intake["sealed_candidate_id"]
    assert action.inputs["provider_job_kind"] == intake["provider_job_kind"]
    assert action.inputs["component_id"] == intake["component_id"]
    assert action.inputs["source_obligation_id"] == intake["source_obligation_id"]
    assert action.inputs["requirement_ids"] == intake["requirement_ids"]
    assert action.inputs["expected_source_classes"] == (intake["expected_source_classes"])
    assert action.inputs["evidence_ledger_intake_mode"] == (AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE)
    assert action.inputs["evidence_ledger_projection_digest"] == (evidence_ledger_projection_digest(ledger_projection))

    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=ledger_projection,
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(result.observation)

    state = kernel.state.followup_sufficiency_recheck_state
    projection = kernel.state.followup_sufficiency_recheck_projection
    assert state["owner"] == "RunKernel.FollowupSufficiencyRecheck"
    assert state["canonical_state"] is True
    assert projection["canonical_state"] is True
    assert projection["evidence_ledger_intake_mode"] == (AG96I3M2_EVIDENCE_LEDGER_INTAKE_MODE)
    assert projection["fixture_sufficiency_posture"] == (FollowupSufficiencyPosture.READY_FOR_NEXT_FIXTURE_PHASE.value)
    expected_candidate = dict(intake["ag96i3m2_admission_review_candidate"])
    expected_candidate.pop("raw_page_text_retained", None)
    assert projection["ag96i3m2_admission_review_candidate"] == expected_candidate
    assert "raw_page_text_retained" not in (projection["ag96i3m2_admission_review_candidate"])
    assert projection["ag96i3m2_evidence_ledger_intake_binding"] == (intake["ag96i3m2_evidence_ledger_intake_binding"])
    assert projection["evidence_ledger_observation_id"] == "ag96i3m2:obs:001"
    assert projection["evidence_ledger_counts"] == {
        "candidate_count": 1,
        "requirement_count": 1,
        "custody_record_count": 1,
        "custody_gap_count": 0,
        "observation_ref_count": 1,
    }
    assert projection["official_current_custody_status"]["source_obligation_satisfied"] is True
    assert projection["final_answer_packet_deferred"] is True
    assert projection["author_activation_allowed"] is False
    assert projection["citation_eligible"] is False
    assert projection["citation_behavior_changed"] is False
    assert _closed_surface_snapshot(kernel) == before


@pytest.mark.parametrize(
    "field",
    [
        "intake_id",
        "execution_id",
        "sealed_candidate_id",
        "requirement_ids",
        "expected_source_classes",
        "evidence_ledger_intake_mode",
        "followup_authorization_consumption_id",
    ],
)
def test_m2_recheck_reducer_rejects_mutated_binding_fields(field: str) -> None:
    kernel = _m2_kernel()
    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    bad_state = deepcopy(result.record.to_dict())
    if field in {"requirement_ids", "expected_source_classes"}:
        bad_state[field] = ["mutated"]
    else:
        bad_state[field] = f"mutated-{field}"

    with pytest.raises(RunKernelTransitionError, match=field):
        kernel.reduce(_observation_from_state(action, bad_state))


def test_m2_recheck_reducer_rejects_stale_evidence_ledger_digest() -> None:
    kernel = _m2_kernel()
    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.state.evidence_ledger.observation_refs.append(
        {"observation_id": "ag96i3n:stale-ledger", "source": "test_mutation"}
    )

    with pytest.raises(RunKernelTransitionError, match="digest mismatch"):
        kernel.reduce(result.observation)


@pytest.mark.parametrize(
    ("projection", "match"),
    [
        ({}, "EvidenceLedger owner"),
        (
            {
                "owner": "RunKernel.EvidenceLedger",
                "canonical_state": False,
                "trace_only": False,
                "requirement_count": 1,
            },
            "canonical EvidenceLedger",
        ),
    ],
)
def test_m2_recheck_runtime_rejects_missing_or_noncanonical_ledger_projection(
    projection: dict[str, Any],
    match: str,
) -> None:
    kernel = _m2_kernel()
    action = kernel.authorize_followup_sufficiency_recheck()

    with pytest.raises(PermissionError, match=match):
        execute_followup_sufficiency_recheck_action(
            action,
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
            evidence_ledger_projection=projection,
        )


def test_m2_recheck_authorization_rejects_invalid_intake_mode() -> None:
    kernel = _m2_kernel()
    kernel.state.followup_evidence_intake_state["evidence_ledger_intake_mode"] = "unknown_intake_mode"

    with pytest.raises(RunKernelTransitionError, match="known intake state"):
        kernel.authorize_followup_sufficiency_recheck()


def test_m2_recheck_authorization_rejects_missing_runtime_intake_flag() -> None:
    kernel = _m2_kernel()
    kernel.state.followup_evidence_intake_state.pop("runtime_evidence_intake_occurred")

    with pytest.raises(RunKernelTransitionError, match="runtime EvidenceLedger intake"):
        kernel.authorize_followup_sufficiency_recheck()


def test_m2_recheck_missing_source_obligation_posture_is_rejected() -> None:
    kernel = _m2_kernel()
    kernel.state.followup_evidence_intake_state.pop("source_obligation_satisfied")

    with pytest.raises(RunKernelTransitionError, match="source obligation posture"):
        kernel.authorize_followup_sufficiency_recheck()


def test_m2_recheck_source_obligation_false_becomes_insufficiency_posture() -> None:
    kernel = _m2_kernel()
    kernel.state.followup_evidence_intake_state["source_obligation_satisfied"] = False

    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.reduce(result.observation)

    projection = kernel.state.followup_sufficiency_recheck_projection
    assert projection["fixture_sufficiency_posture"] == (FollowupSufficiencyPosture.INSUFFICIENT_EVIDENCE.value)
    assert projection["source_requirement_status_summary"]["unsatisfied"] == 1
    assert projection["official_current_custody_status"]["source_obligation_satisfied"] is False
    assert projection["citation_eligible"] is False
    assert projection["final_answer_packet_deferred"] is True
    assert projection["author_activation_allowed"] is False


def test_m2_recheck_keeps_final_answer_author_and_live_surfaces_closed() -> None:
    kernel = _m2_kernel()
    before = _closed_surface_snapshot(kernel)

    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.reduce(result.observation)

    assert _closed_surface_snapshot(kernel) == before
    flags = kernel.state.followup_sufficiency_recheck_projection["behavior_boundary_flags"]
    for flag in (
        "live_provider_call_executed",
        "search_executed",
        "retrieval_executed",
        "fetch_executed",
        "model_called",
        "query_generation_changed",
        "retrieval_ranking_filtering_changed",
        "final_answer_packet_updated",
        "final_answer_behavior_changed",
        "author_prose_behavior_changed",
        "citation_behavior_changed",
    ):
        assert flags[flag] is False


def test_static_guards_keep_ag96i3n_closed_to_live_prompt_and_orchestrator() -> None:
    module_paths = [
        ROOT / "core" / "followup_sufficiency_recheck_runtime.py",
        ROOT / "core" / "followup_runkernel_reducers.py",
    ]
    forbidden_imports = {
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.prompts",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
    }
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        if path.name == "followup_sufficiency_recheck_runtime.py":
            assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for forbidden in (
            "requests.",
            "httpx.",
            "urlopen",
            "ask_model",
            "select_providers",
            "format_citation",
            "AuthorExecutor(",
            "FinalAnswerPacket(",
        ):
            assert forbidden not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(encoding="utf-8")
    assert "ag96i3n" not in pipeline_source.casefold()
    assert "followup_sufficiency_recheck_runtime" not in pipeline_source


def _m2_kernel() -> RunKernel:
    kernel = run_followup_through_execution(run_id=RUN_ID)
    _execute_m2_intake(kernel)
    return kernel


def _observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_sufficiency_recheck_observed",
        status="completed",
        payload={"followup_sufficiency_recheck_state": state},
    )


def _closed_surface_snapshot(kernel: RunKernel) -> dict[str, Any]:
    return {
        "run_contract": deepcopy(kernel.state.run_contract),
        "run_contract_projection": deepcopy(kernel.state.run_contract_projection),
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(kernel.state.final_answer_authority_projection),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
        "followup_final_answer_packet_state": deepcopy(kernel.state.followup_final_answer_packet_state),
        "followup_author_gate_state": deepcopy(kernel.state.followup_author_gate_state),
        "followup_author_observation_state": deepcopy(kernel.state.followup_author_observation_state),
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
