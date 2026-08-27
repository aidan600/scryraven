from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import SourceRequirementStatus
from core.followup_deliberation import GapType
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    FollowupSufficiencyPosture,
    execute_followup_sufficiency_recheck_action,
)
from core.run_authority_sufficiency import RunSufficiencyDecision
from core.run_kernel import (
    FOLLOWUP_SUFFICIENCY_RECHECK_STAGE,
    RUN_KERNEL_TRACE_KEY,
    SUFFICIENCY_JUDGMENT_STAGE,
    Observation,
    RunKernelTransitionError,
)
from tests.helpers.followup_fixture_spine import (
    build_followup_fixture_checkpoint,
    consume_followup_sufficiency_recheck,
    followup_fixture_gap,
    followup_fixture_payload,
    run_followup_through_evidence_intake,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i2d-fixture"


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def test_happy_path_rechecks_sufficiency_from_updated_evidence_ledger() -> None:
    kernel = run_followup_through_evidence_intake(run_id=RUN_ID)

    consume_followup_sufficiency_recheck(kernel)

    state = kernel.state.followup_sufficiency_recheck_state
    projection = kernel.state.followup_sufficiency_recheck_projection
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert state["owner"] == "RunKernel.FollowupSufficiencyRecheck"
    assert state["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["fixture_sufficiency_posture"] == (
        FollowupSufficiencyPosture.READY_FOR_NEXT_FIXTURE_PHASE.value
    )
    assert projection["final_answer_packet_deferred"] is True
    assert projection["author_activation_allowed"] is False
    assert projection["citation_behavior_changed"] is False
    assert sufficiency["owner"] == "RunKernel.RunAuthoritySufficiencyJudgment"
    assert sufficiency["canonical_state"] is True
    assert sufficiency["final_answer_allowed"] is False
    assert "fixture_only_sufficiency_recheck_final_answer_deferred" in (
        sufficiency["mandatory_caveats"]
    )
    assert kernel.state.projections[SUFFICIENCY_JUDGMENT_STAGE] == sufficiency
    assert kernel.state.projections[FOLLOWUP_SUFFICIENCY_RECHECK_STAGE] == projection
    assert kernel.state.followup_sufficiency_recheck_history == [projection]
    assert kernel.state.sufficiency_judgment_history[-1] == sufficiency
    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]
    assert trace["followup_sufficiency_recheck_projection"] == projection
    assert trace["sufficiency_judgment_projection"] == sufficiency
    assert kernel.state.final_answer_packet == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_authority_projection == {}


def test_recheck_outcome_reflects_evidence_ledger_statuses() -> None:
    kernel = run_followup_through_evidence_intake(run_id=RUN_ID)
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value

    consume_followup_sufficiency_recheck(kernel)

    summary = kernel.state.followup_sufficiency_recheck_projection[
        "source_requirement_status_summary"
    ]
    assert summary["satisfied"] == 1
    assert summary["all_satisfied"] is True
    assert kernel.state.sufficiency_judgment_projection["satisfied_obligations"]


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ({"bridge_only": True}, SourceRequirementStatus.UNSATISFIED.value),
        ({"no_result": True}, SourceRequirementStatus.UNSATISFIED.value),
        (
            {"wrong_source_class": True, "source_class": "reputable_secondary"},
            SourceRequirementStatus.UNSATISFIED.value,
        ),
        ({"error": "sanitized fixture error"}, SourceRequirementStatus.UNSATISFIED.value),
    ],
)
def test_bridge_only_no_result_wrong_class_and_error_remain_non_sufficient(
    payload: dict[str, Any],
    expected_status: str,
) -> None:
    kernel = run_followup_through_evidence_intake(
        run_id=RUN_ID,
        fixture_payload=followup_fixture_payload(**payload),
    )

    consume_followup_sufficiency_recheck(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == expected_status
    assert kernel.state.followup_sufficiency_recheck_projection[
        "fixture_sufficiency_posture"
    ] in {
        FollowupSufficiencyPosture.ANSWER_WITH_CAVEATS.value,
        FollowupSufficiencyPosture.INSUFFICIENT_EVIDENCE.value,
    }
    assert kernel.state.sufficiency_judgment_projection["final_answer_allowed"] is False
    assert kernel.state.followup_sufficiency_recheck_projection[
        "author_activation_allowed"
    ] is False


def test_reducer_rejects_observation_bound_to_different_intake() -> None:
    kernel = run_followup_through_evidence_intake(run_id=RUN_ID)
    action_for_a = kernel.authorize_followup_sufficiency_recheck()
    result_for_a = execute_followup_sufficiency_recheck_action(
        action_for_a,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    bad_state = deepcopy(result_for_a.record.to_dict())
    bad_state["intake_id"] = "followup-evidence-intake:other"
    bad_state["followup_evidence_intake_id"] = "followup-evidence-intake:other"
    bad_observation = Observation.from_action(
        action_for_a,
        observation_type="followup_sufficiency_recheck_observed",
        status="completed",
        payload={"followup_sufficiency_recheck_state": bad_state},
    )

    with pytest.raises(RunKernelTransitionError, match="intake_id"):
        kernel.reduce(bad_observation)


def test_authorization_inputs_cannot_override_canonical_binding_fields() -> None:
    kernel = run_followup_through_evidence_intake(run_id=RUN_ID)
    action = kernel.authorize_followup_sufficiency_recheck(
        inputs={
            "intake_id": "malicious-intake",
            "execution_id": "malicious-execution",
            "sealed_candidate_id": "auth.candidate.999",
            "requirement_ids": ["malicious-requirement"],
            "expected_source_classes": ["reputable_secondary"],
            "provider_job_kind": "semantic_recall",
            "component_id": "component-other",
            "source_obligation_id": "obligation-other",
            "sufficiency_recheck_mode": "live",
            "final_answer_packet_deferred": False,
            "author_activation_allowed": True,
            "caller_note": "preserved_non_binding_input",
        }
    )
    intake = kernel.state.followup_evidence_intake_state
    assert action.inputs["intake_id"] == intake["intake_id"]
    assert action.inputs["execution_id"] == intake["execution_id"]
    assert action.inputs["sealed_candidate_id"] == intake["sealed_candidate_id"]
    assert action.inputs["requirement_ids"] == intake["requirement_ids"]
    assert action.inputs["expected_source_classes"] == intake["expected_source_classes"]
    assert action.inputs["provider_job_kind"] == intake["provider_job_kind"]
    assert action.inputs["component_id"] == intake["component_id"]
    assert action.inputs["source_obligation_id"] == intake["source_obligation_id"]
    assert action.inputs["sufficiency_recheck_mode"] == FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    assert action.inputs["final_answer_packet_deferred"] is True
    assert action.inputs["author_activation_allowed"] is False
    assert action.inputs["caller_note"] == "preserved_non_binding_input"


def test_observation_spoofing_ready_author_and_citation_fields_are_overwritten() -> None:
    kernel = run_followup_through_evidence_intake(
        run_id=RUN_ID,
        fixture_payload=followup_fixture_payload(bridge_only=True),
    )
    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed["fixture_sufficiency_posture"] = (
        FollowupSufficiencyPosture.READY_FOR_NEXT_FIXTURE_PHASE.value
    )
    spoofed["final_answer_packet_deferred"] = False
    spoofed["author_activation_allowed"] = True
    spoofed["citation_eligible"] = True
    spoofed["citation_behavior_changed"] = True
    spoofed["sufficiency_judgment_projection"]["decision"] = (
        RunSufficiencyDecision.READY_DIRECT.value
    )
    spoofed["sufficiency_judgment_projection"]["required_obligations_satisfied"] = True
    spoofed["sufficiency_judgment_projection"]["final_answer_allowed"] = True
    observation = Observation.from_action(
        action,
        observation_type="followup_sufficiency_recheck_observed",
        status="completed",
        payload={"followup_sufficiency_recheck_state": spoofed},
    )

    kernel.reduce(observation)

    projection = kernel.state.followup_sufficiency_recheck_projection
    sufficiency = kernel.state.sufficiency_judgment_projection
    assert projection["fixture_sufficiency_posture"] == (
        FollowupSufficiencyPosture.ANSWER_WITH_CAVEATS.value
    )
    assert projection["final_answer_packet_deferred"] is True
    assert projection["author_activation_allowed"] is False
    assert projection["citation_eligible"] is False
    assert projection["citation_behavior_changed"] is False
    assert sufficiency["final_answer_allowed"] is False
    assert sufficiency["required_obligations_satisfied"] is False


def test_source_bound_numeric_unknown_remains_unknown_without_quant_resolution() -> None:
    checkpoint = build_followup_fixture_checkpoint(
        run_id=RUN_ID,
        gaps=[
            followup_fixture_gap(
                GapType.SOURCE_BOUND_NUMERIC_GAP.value,
                gap_id="gap.numeric",
                obligation_id="obligation-source-bound-numeric",
                requirement_id="requirement-source-bound-numeric",
            )
        ]
    )
    kernel = run_followup_through_evidence_intake(
        run_id=RUN_ID,
        checkpoint=checkpoint,
        fixture_payload=followup_fixture_payload(
            source_class="sourced_numeric_values",
            source_tier="official",
            title="Numeric source fixture",
        ),
    )

    consume_followup_sufficiency_recheck(kernel)

    assert kernel.state.followup_sufficiency_recheck_projection[
        "fixture_sufficiency_posture"
    ] == FollowupSufficiencyPosture.SOURCE_BOUND_UNKNOWN.value
    assert kernel.state.sufficiency_judgment_projection[
        "source_bound_numeric_unknowns"
    ]
    assert "do_not_present_source_bound_numeric_unknown_as_known" in (
        kernel.state.sufficiency_judgment_projection["prohibited_upgrades"]
    )


def test_recheck_preserves_closed_search_final_answer_author_and_citation_surfaces() -> None:
    kernel = run_followup_through_evidence_intake(run_id=RUN_ID)
    before = {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }

    consume_followup_sufficiency_recheck(kernel)

    assert kernel.state.final_answer_packet == before["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == (
        before["final_answer_authority_projection"]
    )
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    flags = kernel.state.followup_sufficiency_recheck_projection[
        "behavior_boundary_flags"
    ]
    assert flags["final_answer_packet_updated"] is False
    assert flags["citation_behavior_changed"] is False
    assert flags["author_activation_allowed"] is False


def test_static_guards_keep_recheck_closed_to_live_surfaces_and_orchestrator() -> None:
    module_paths = [
        ROOT / "core" / "followup_sufficiency_recheck_runtime.py",
        ROOT / "core" / "followup_evidence_intake_runtime.py",
        ROOT / "core" / "followup_execution_runtime.py",
    ]
    forbidden_imports = {
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.pipeline_orchestrator",
        "subprocess",
        "os",
        "requests",
        "openai",
    }
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
        for token in (
            "ask_model",
            "process_search_queries",
            "select_providers",
            "format_citation",
            "FinalAnswerPacket(",
            "AuthorExecutor",
        ):
            assert token not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_sufficiency_recheck_runtime" not in pipeline_source
    assert "FOLLOWUP_SUFFICIENCY_RECHECK_STAGE" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
