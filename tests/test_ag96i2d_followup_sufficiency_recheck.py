from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.evidence_ledger import SourceRequirementStatus
from core.followup_authorization_runtime import (
    execute_followup_authorization_consumption_action,
)
from core.followup_deliberation import (
    GapType,
    build_followup_deliberation_checkpoint,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_evidence_intake_runtime import (
    execute_followup_evidence_intake_action,
)
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    execute_followup_fixture_action,
)
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
    RunKernel,
    RunKernelTransitionError,
)

ROOT = Path(__file__).resolve().parents[1]


def _budget(**overrides: int) -> dict[str, int]:
    base = {
        "cost_points_remaining": 8,
        "provider_calls_remaining": 3,
        "fetches_remaining": 3,
        "read_units_remaining": 3,
        "followup_rounds_remaining": 2,
        "meso_authorizations_remaining": 3,
        "macro_hops_remaining": 1,
    }
    base.update(overrides)
    return base


def _component(component_id: str, *, served: bool = True) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "central": True,
        "served_minimum": served,
        "minimum_provider_calls": 1,
        "minimum_fetches": 1,
        "minimum_read_units": 1,
    }


def _gap(
    gap_type: str,
    *,
    gap_id: str = "gap.official",
    component_id: str = "component-rule",
    obligation_id: str = "obligation-official-current",
    requirement_id: str = "requirement-official-current",
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "gap_id": gap_id,
        "gap_type": gap_type,
        "component_id": component_id,
        "source_obligation_id": obligation_id,
        "requirement_ids": [requirement_id],
        "severity": "central_required",
        "evidence_indicators": ["required_obligation_unsatisfied"],
    }
    payload.update(overrides)
    return payload


def _checkpoint(**overrides: Any) -> Any:
    fixture = {
        "run_id": "ag96i2d-fixture",
        "checkpoint_id": "after-first-pass",
        "mode": "balanced",
        "components": [_component("component-rule")],
        "budget_ledger": _budget(),
        "gaps": [_gap(GapType.OFFICIAL_CURRENT_GAP.value)],
        "sufficiency_handoff": {
            "satisfied_obligations": [],
            "missing_obligations": ["obligation-official-current"],
            "recommended_final_posture": "answer_with_caveats",
            "mandatory_caveats": ["prior_missing_official_current_caveat"],
            "prohibited_upgrades": ["prior_do_not_upgrade_fixture_gap"],
        },
    }
    fixture.update(overrides)
    return build_followup_deliberation_checkpoint(fixture)


def _fixture_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "result_status": "fixture_success",
        "summary": "Sanitized official current fixture candidate observed.",
        "url": "https://agency.example/current-rule",
        "title": "Current Official Rule",
        "domain": "agency.example",
        "source_tier": "official",
        "source_class": "official_current_rules",
        "currentness_signal": "current",
        "answer_bearing_extract_available": True,
        "eligible_for_stronger_obligation": True,
    }
    payload.update(overrides)
    return payload


def _authorize_execute_intake(
    *,
    checkpoint: Any | None = None,
    fixture_payload: dict[str, Any] | None = None,
) -> RunKernel:
    kernel = RunKernel.start(run_id="ag96i2d-fixture", request_id="request-1")
    auth_action = kernel.authorize_followup_authorization_consumption(
        inputs={"checkpoint_id": "after-first-pass"}
    )
    auth_result = execute_followup_authorization_consumption_action(
        auth_action,
        checkpoint=checkpoint or _checkpoint(),
    )
    kernel.reduce(auth_result.observation)
    exec_action = kernel.authorize_followup_fixture_execution(
        candidate_id="auth.candidate.001",
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )
    exec_result = execute_followup_fixture_action(
        exec_action,
        authorization_state=kernel.state.followup_authorization_state,
        sealed_candidate_id="auth.candidate.001",
        fixture_result_payload=fixture_payload or _fixture_payload(),
        execution_mode=FIXTURE_EXECUTION_MODE,
    )
    kernel.reduce(exec_result.observation)
    intake_action = kernel.authorize_followup_evidence_intake()
    intake_result = execute_followup_evidence_intake_action(
        intake_action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.reduce(intake_result.observation)
    return kernel


def _recheck(kernel: RunKernel) -> None:
    action = kernel.authorize_followup_sufficiency_recheck()
    result = execute_followup_sufficiency_recheck_action(
        action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(result.observation)


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def test_happy_path_rechecks_sufficiency_from_updated_evidence_ledger() -> None:
    kernel = _authorize_execute_intake()

    _recheck(kernel)

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
    kernel = _authorize_execute_intake()
    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value

    _recheck(kernel)

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
    kernel = _authorize_execute_intake(fixture_payload=_fixture_payload(**payload))

    _recheck(kernel)

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
    kernel = _authorize_execute_intake()
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
    kernel = _authorize_execute_intake()
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
    kernel = _authorize_execute_intake(fixture_payload=_fixture_payload(bridge_only=True))
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
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.SOURCE_BOUND_NUMERIC_GAP.value,
                gap_id="gap.numeric",
                obligation_id="obligation-source-bound-numeric",
                requirement_id="requirement-source-bound-numeric",
            )
        ]
    )
    kernel = _authorize_execute_intake(
        checkpoint=checkpoint,
        fixture_payload=_fixture_payload(
            source_class="sourced_numeric_values",
            source_tier="official",
            title="Numeric source fixture",
        ),
    )

    _recheck(kernel)

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
    kernel = _authorize_execute_intake()
    before = {
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }

    _recheck(kernel)

    assert kernel.state.search_judgment == before["search_judgment"]
    assert kernel.state.search_judgment_projection == before["search_judgment_projection"]
    assert kernel.state.final_answer_packet == before["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == (
        before["final_answer_authority_projection"]
    )
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    flags = kernel.state.followup_sufficiency_recheck_projection[
        "behavior_boundary_flags"
    ]
    assert flags["search_judgment_rerun"] is False
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
