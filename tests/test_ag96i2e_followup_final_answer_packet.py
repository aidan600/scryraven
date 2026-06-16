from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_authorization_runtime import (
    execute_followup_authorization_consumption_action,
)
from core.followup_deliberation import GapType, build_followup_deliberation_checkpoint
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_evidence_intake_runtime import execute_followup_evidence_intake_action
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    execute_followup_fixture,
    execute_followup_fixture_action,
)
from core.followup_final_answer_packet_runtime import (
    FOLLOWUP_FINAL_ANSWER_PACKET_MODE,
    execute_followup_final_answer_packet_prepare_action,
)
from core.followup_sufficiency_recheck_runtime import (
    FOLLOWUP_SUFFICIENCY_RECHECK_MODE,
    execute_followup_sufficiency_recheck_action,
)
from core.run_kernel import (
    FINAL_ANSWER_PACKET_STAGE,
    FOLLOWUP_FINAL_ANSWER_PACKET_STAGE,
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
        "run_id": "ag96i2e-fixture",
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


def _through_recheck(
    *,
    checkpoint: Any | None = None,
    fixture_payload: dict[str, Any] | None = None,
    prior_sufficiency: dict[str, Any] | None = None,
) -> RunKernel:
    kernel = RunKernel.start(run_id="ag96i2e-fixture", request_id="request-1")
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
    if prior_sufficiency is not None:
        kernel.state.sufficiency_judgment_projection = prior_sufficiency
    recheck_action = kernel.authorize_followup_sufficiency_recheck()
    recheck_result = execute_followup_sufficiency_recheck_action(
        recheck_action,
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        prior_sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        sufficiency_handoff=kernel.state.followup_authorization_state.get(
            "sufficiency_handoff",
            {},
        ),
    )
    kernel.reduce(recheck_result.observation)
    return kernel


def _prepare_packet(kernel: RunKernel):
    action = kernel.authorize_followup_final_answer_packet_prepare()
    result = execute_followup_final_answer_packet_prepare_action(
        action,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    kernel.reduce(result.observation)
    return action, result


def test_happy_path_prepares_fixture_only_packet_from_rechecked_state() -> None:
    kernel = _through_recheck()
    before_observed = deepcopy(kernel.state.final_answer_packet)

    _action, result = _prepare_packet(kernel)

    state = kernel.state.followup_final_answer_packet_state
    projection = kernel.state.followup_final_answer_packet_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    assert before_observed == {}
    assert state["owner"] == "RunKernel.FollowupFinalAnswerPacket"
    assert state["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["final_answer_packet_prepared"] is True
    assert projection["author_activation_allowed"] is False
    assert projection["author_execution_deferred"] is True
    assert projection["citation_rendering_changed"] is False
    assert projection["citation_formatter_invoked"] is False
    assert projection["product_answer_behavior_changed"] is False
    assert packet["packet_id"] == result.record.to_dict()["packet_id"]
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert authority["owner"] == "RunKernel.FinalAnswerPacket"
    assert authority["canonical_state"] is True
    assert authority["author_payload_ref"]["status"] == "author_execution_deferred"
    assert authority["author_activation_allowed"] is False
    assert kernel.state.projections[FINAL_ANSWER_PACKET_STAGE] == authority
    assert kernel.state.projections[FOLLOWUP_FINAL_ANSWER_PACKET_STAGE] == projection
    assert kernel.state.followup_final_answer_packet_history == [projection]
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    with pytest.raises(RunKernelTransitionError, match="author input payload"):
        kernel.authorize_author_execution()


def test_packet_consumes_sufficiency_caveats_obligations_unknowns_and_conflicts() -> None:
    prior = {
        "owner": "RunKernel.RunAuthoritySufficiencyJudgment",
        "canonical_state": True,
        "trace_only": False,
        "unresolved_conflicts": ["conflict-currentness"],
        "mandatory_caveats": ["prior_conflict_must_be_caveated"],
        "prohibited_upgrades": ["prior_do_not_resolve_conflict_without_source"],
    }
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
    kernel = _through_recheck(
        checkpoint=checkpoint,
        fixture_payload=_fixture_payload(
            source_class="sourced_numeric_values",
            source_tier="official",
            title="Numeric source fixture",
        ),
        prior_sufficiency=prior,
    )

    _prepare_packet(kernel)

    packet = kernel.state.final_answer_packet
    projection = kernel.state.followup_final_answer_packet_projection
    assert "prior_conflict_must_be_caveated" in packet["mandatory_caveats"]
    assert "missing_source_bound_numeric_value_remains_unknown" in (
        packet["mandatory_caveats"]
    )
    assert "prior_do_not_resolve_conflict_without_source" in (
        packet["prohibited_upgrades"]
    )
    assert "do_not_present_source_bound_numeric_unknown_as_known" in (
        packet["prohibited_upgrades"]
    )
    assert projection["source_bound_unknowns"]
    assert "unresolved_central_conflict" in projection["unresolved_conflicts"]
    assert packet["final_answer_allowed"] is False
    assert projection["author_execution_deferred"] is True


def test_packet_eligible_evidence_refs_come_from_accepted_ledger_custody() -> None:
    kernel = _through_recheck()

    _prepare_packet(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    accepted_candidate_id = ledger["candidate_records"][0]["candidate_id"]
    packet = kernel.state.final_answer_packet
    projection = kernel.state.followup_final_answer_packet_projection
    assert packet["evidence_allowed"][0]["source_id"] == accepted_candidate_id
    assert packet["citation_eligible"][0]["source_id"] == accepted_candidate_id
    assert projection["final_evidence_refs"][0]["source_id"] == accepted_candidate_id
    assert projection["citation_eligibility_refs"][0]["source_id"] == (
        accepted_candidate_id
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"bridge_only": True},
        {"no_result": True},
        {"wrong_source_class": True, "source_class": "reputable_secondary"},
        {"error": "sanitized fixture error"},
    ],
)
def test_non_satisfying_ledger_candidates_do_not_become_packet_eligible(
    payload: dict[str, Any],
) -> None:
    kernel = _through_recheck(fixture_payload=_fixture_payload(**payload))

    _prepare_packet(kernel)

    assert kernel.state.final_answer_packet["evidence_allowed"] == []
    assert kernel.state.final_answer_packet["citation_eligible"] == []
    assert kernel.state.followup_final_answer_packet_projection[
        "final_evidence_refs"
    ] == []
    assert kernel.state.followup_final_answer_packet_projection[
        "citation_eligibility_refs"
    ] == []


def test_reducer_rejects_observation_bound_to_different_recheck() -> None:
    kernel = _through_recheck()
    action = kernel.authorize_followup_final_answer_packet_prepare()
    result = execute_followup_final_answer_packet_prepare_action(
        action,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    bad_state = deepcopy(result.record.to_dict())
    bad_state["recheck_id"] = "followup-sufficiency-recheck:other"
    bad_state["followup_sufficiency_recheck_id"] = (
        "followup-sufficiency-recheck:other"
    )
    bad_observation = Observation.from_action(
        action,
        observation_type="followup_final_answer_packet_prepared",
        status="completed",
        payload={"followup_final_answer_packet_state": bad_state},
    )

    with pytest.raises(RunKernelTransitionError, match="recheck_id"):
        kernel.reduce(bad_observation)


def test_authorization_inputs_cannot_override_canonical_packet_bindings() -> None:
    kernel = _through_recheck()
    action = kernel.authorize_followup_final_answer_packet_prepare(
        inputs={
            "packet_id": "malicious-packet",
            "recheck_id": "malicious-recheck",
            "intake_id": "malicious-intake",
            "execution_id": "malicious-execution",
            "sealed_candidate_id": "auth.candidate.999",
            "requirement_ids": ["malicious-requirement"],
            "expected_source_classes": ["reputable_secondary"],
            "provider_job_kind": "semantic_recall",
            "component_id": "component-other",
            "source_obligation_id": "obligation-other",
            "final_answer_packet_mode": "live",
            "author_activation_allowed": True,
            "citation_rendering_changed": True,
            "product_answer_behavior_changed": True,
            "live_validation_not_run": False,
            "caller_note": "preserved_non_binding_input",
        }
    )
    recheck = kernel.state.followup_sufficiency_recheck_state
    assert action.inputs["recheck_id"] == recheck["recheck_id"]
    assert action.inputs["intake_id"] == recheck["intake_id"]
    assert action.inputs["execution_id"] == recheck["execution_id"]
    assert action.inputs["sealed_candidate_id"] == recheck["sealed_candidate_id"]
    assert action.inputs["requirement_ids"] == recheck["requirement_ids"]
    assert action.inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert action.inputs["provider_job_kind"] == recheck["provider_job_kind"]
    assert action.inputs["component_id"] == recheck["component_id"]
    assert action.inputs["source_obligation_id"] == recheck["source_obligation_id"]
    assert action.inputs["final_answer_packet_mode"] == (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    )
    assert action.inputs["author_activation_allowed"] is False
    assert action.inputs["citation_rendering_changed"] is False
    assert action.inputs["product_answer_behavior_changed"] is False
    assert action.inputs["live_validation_not_run"] is True
    assert action.inputs["caller_note"] == "preserved_non_binding_input"


def test_observation_spoofing_is_overwritten_by_canonical_packet_derivation() -> None:
    kernel = _through_recheck()
    action = kernel.authorize_followup_final_answer_packet_prepare()
    result = execute_followup_final_answer_packet_prepare_action(
        action,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed["author_activation_allowed"] = True
    spoofed["author_execution_deferred"] = False
    spoofed["citation_rendering_changed"] = True
    spoofed["citation_formatter_invoked"] = True
    spoofed["product_answer_behavior_changed"] = True
    spoofed["live_validation_not_run"] = False
    spoofed["final_evidence_refs"] = [
        {"source_id": "bridge-only", "candidate_id": "bridge-only"}
    ]
    spoofed["packet_projection"]["evidence_allowed"] = [
        {"source_id": "bridge-only", "evidence_id": "bad"}
    ]
    spoofed["packet_projection"]["mandatory_caveats"] = []
    spoofed["packet_projection"]["prohibited_upgrades"] = []
    spoofed["packet_projection"]["source_bound_numeric_unknowns"] = []
    observation = Observation.from_action(
        action,
        observation_type="followup_final_answer_packet_prepared",
        status="completed",
        payload={"followup_final_answer_packet_state": spoofed},
    )

    kernel.reduce(observation)

    projection = kernel.state.followup_final_answer_packet_projection
    packet = kernel.state.final_answer_packet
    accepted_candidate_id = (
        kernel.state.evidence_ledger.to_projection().to_dict()["candidate_records"][0][
            "candidate_id"
        ]
    )
    assert projection["author_activation_allowed"] is False
    assert projection["author_execution_deferred"] is True
    assert projection["citation_rendering_changed"] is False
    assert projection["citation_formatter_invoked"] is False
    assert projection["product_answer_behavior_changed"] is False
    assert projection["live_validation_not_run"] is True
    assert projection["final_evidence_refs"][0]["source_id"] == accepted_candidate_id
    assert "fixture_only_final_answer_packet_author_deferred" in (
        packet["mandatory_caveats"]
    )
    assert "do_not_activate_author_from_fixture_only_final_answer_packet" in (
        packet["prohibited_upgrades"]
    )


def test_closed_surfaces_remain_closed_and_orchestrator_is_untouched() -> None:
    kernel = _through_recheck()
    before = {
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }

    _prepare_packet(kernel)

    assert kernel.state.search_judgment == before["search_judgment"]
    assert kernel.state.search_judgment_projection == before[
        "search_judgment_projection"
    ]
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    flags = kernel.state.followup_final_answer_packet_projection[
        "behavior_boundary_flags"
    ]
    assert flags["author_executor_invoked"] is False
    assert flags["citation_formatter_invoked"] is False
    assert flags["product_answer_behavior_changed"] is False
    assert flags["search_judgment_rerun"] is False

    module_paths = [
        ROOT / "core" / "followup_final_answer_packet_runtime.py",
        ROOT / "core" / "followup_sufficiency_recheck_runtime.py",
        ROOT / "core" / "followup_evidence_intake_runtime.py",
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
    packet_source = (ROOT / "core" / "followup_final_answer_packet_runtime.py").read_text(
        encoding="utf-8"
    )
    for token in (
        "ask_model",
        "select_author_system_prompt",
        "to_author_input_payload",
        "format_citation",
        "AuthorExecutor",
    ):
        assert token not in packet_source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_final_answer_packet_runtime" not in pipeline_source
    assert "FOLLOWUP_FINAL_ANSWER_PACKET_STAGE" not in pipeline_source


def test_second_packet_prepare_for_same_recheck_is_rejected() -> None:
    kernel = _through_recheck()

    _prepare_packet(kernel)

    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_final_answer_packet_prepare()


def test_adapter_requires_authorized_action_type() -> None:
    kernel = _through_recheck()
    wrong_action = kernel.authorize_followup_sufficiency_recheck()

    with pytest.raises(ValueError, match="authorized action type"):
        execute_followup_final_answer_packet_prepare_action(
            wrong_action,
            followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
            sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
            evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
            followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
        )


def test_cross_recheck_observation_from_second_fixture_is_rejected() -> None:
    kernel = _through_recheck()
    action_for_a = kernel.authorize_followup_final_answer_packet_prepare()
    candidate_b = deepcopy(kernel.state.followup_authorization_state["sealed_candidates"][0])
    candidate_b["candidate_id"] = "auth.candidate.002"
    candidate_b["seal_id"] = "seal:after-first-pass:auth.candidate.002"
    kernel.state.followup_authorization_state["sealed_candidates"].append(candidate_b)
    b_execution = execute_followup_fixture(
        kernel.state.followup_authorization_state,
        sealed_candidate_id="auth.candidate.002",
        fixture_result_payload=_fixture_payload(title="Candidate B"),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()

    result_for_a = execute_followup_final_answer_packet_prepare_action(
        action_for_a,
        followup_sufficiency_recheck_state=kernel.state.followup_sufficiency_recheck_state,
        sufficiency_judgment_projection=kernel.state.sufficiency_judgment_projection,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
        followup_evidence_intake_state=kernel.state.followup_evidence_intake_state,
    )
    bad_state = deepcopy(result_for_a.record.to_dict())
    bad_state["sealed_candidate_id"] = b_execution["sealed_candidate_id"]
    bad_observation = Observation.from_action(
        action_for_a,
        observation_type="followup_final_answer_packet_prepared",
        status="completed",
        payload={"followup_final_answer_packet_state": bad_state},
    )

    with pytest.raises(RunKernelTransitionError, match="sealed_candidate_id"):
        kernel.reduce(bad_observation)


def test_packet_authorization_binds_sufficiency_and_recheck_digests() -> None:
    kernel = _through_recheck()
    action = kernel.authorize_followup_final_answer_packet_prepare()

    assert action.inputs["sufficiency_recheck_mode"] == FOLLOWUP_SUFFICIENCY_RECHECK_MODE
    assert action.inputs["sufficiency_judgment_digest"]
    assert action.inputs["followup_sufficiency_recheck_digest"]
    assert action.inputs["evidence_ledger_projection_digest"]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
