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
    FOLLOWUP_EVIDENCE_INTAKE_MODE,
    execute_followup_evidence_intake_action,
)
from core.followup_execution_runtime import (
    FIXTURE_EXECUTION_MODE,
    execute_followup_fixture,
    execute_followup_fixture_action,
)
from core.run_kernel import (
    EVIDENCE_LEDGER_STAGE,
    FOLLOWUP_EVIDENCE_INTAKE_STAGE,
    RUN_KERNEL_TRACE_KEY,
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
        "run_id": "ag96i2c-fixture",
        "checkpoint_id": "after-first-pass",
        "mode": "balanced",
        "components": [_component("component-rule")],
        "budget_ledger": _budget(),
        "gaps": [_gap(GapType.OFFICIAL_CURRENT_GAP.value)],
        "sufficiency_handoff": {
            "satisfied_obligations": [],
            "missing_obligations": ["obligation-official-current"],
            "recommended_final_posture": "answer_with_caveats",
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


def _authorize_and_execute(
    *,
    checkpoint: Any | None = None,
    fixture_payload: dict[str, Any] | None = None,
) -> RunKernel:
    kernel = RunKernel.start(run_id="ag96i2c-fixture", request_id="request-1")
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
    return kernel


def _intake(kernel: RunKernel) -> None:
    intake_action = kernel.authorize_followup_evidence_intake()
    intake_result = execute_followup_evidence_intake_action(
        intake_action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    kernel.reduce(intake_result.observation)


def _intake_with_mutated_accepted_ledger_payload(kernel: RunKernel) -> None:
    action = kernel.authorize_followup_evidence_intake()
    result = execute_followup_evidence_intake_action(
        action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    payload = deepcopy(result.record.to_dict())
    payload["ledger_candidates"][0]["disposition"] = "accepted"
    payload["ledger_candidates"][0]["eligible_for_stronger_obligation"] = True
    payload["ledger_candidates"][0]["final_evidence_eligible"] = True
    payload["ledger_requirement_links"][0]["link_status"] = "accepted"
    payload["ledger_observation"]["final_evidence"] = [
        {
            "source_id": "malicious-final",
            "url": "https://example.com/malicious",
            "title": "malicious final evidence",
        }
    ]
    observation = Observation.from_action(
        action,
        observation_type="followup_evidence_intake_observed",
        status="completed",
        payload={"followup_evidence_intake_state": payload},
    )
    kernel.reduce(observation)


def _requirement(projection: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for requirement in projection["source_requirements"]:
        if requirement["requirement_id"] == requirement_id:
            return requirement
    raise AssertionError(f"missing requirement {requirement_id}")


def test_followup_fixture_success_intakes_into_evidence_ledger_and_kernel_state() -> None:
    kernel = _authorize_and_execute()
    before = kernel.state.evidence_ledger.to_projection().to_dict()

    _intake(kernel)

    after = kernel.state.evidence_ledger.to_projection().to_dict()
    assert before["candidate_count"] == 0
    assert after["candidate_count"] == 1
    assert after["custody_record_count"] == 1
    assert kernel.state.projections[EVIDENCE_LEDGER_STAGE] == after
    candidate = after["candidate_records"][0]
    assert candidate["provider_name"] == "followup_fixture"
    assert candidate["provider_role"] == "official_current_candidate_acquisition"
    assert "component_rule" in candidate["source_label"]
    assert candidate["source_class"] == "official_current_rules"
    assert candidate["currentness_signal"] == "current"
    assert candidate["final_evidence_eligible"] is False
    requirement = _requirement(after, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert requirement["required_source_class"] == "official_current_rules"

    state = kernel.state.followup_evidence_intake_state
    projection = kernel.state.followup_evidence_intake_projection
    assert state["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["intake_id"] == state["intake_id"]
    assert kernel.state.projections[FOLLOWUP_EVIDENCE_INTAKE_STAGE] == projection
    assert kernel.state.followup_evidence_intake_history == [projection]
    trace = kernel.to_trace_fragment()[RUN_KERNEL_TRACE_KEY]
    assert trace["followup_evidence_intake_state"] == state
    assert trace["followup_evidence_intake_projection"] == projection


def test_intake_reducer_rejects_observation_bound_to_different_execution() -> None:
    kernel = _authorize_and_execute()
    candidate_b = deepcopy(kernel.state.followup_authorization_state["sealed_candidates"][0])
    candidate_b["candidate_id"] = "auth.candidate.002"
    candidate_b["seal_id"] = "seal:after-first-pass:auth.candidate.002"
    candidate_b["provider_job_kind"] = "direct_candidate_search"
    kernel.state.followup_authorization_state["sealed_candidates"].append(candidate_b)
    b_execution = execute_followup_fixture(
        kernel.state.followup_authorization_state,
        sealed_candidate_id="auth.candidate.002",
        fixture_result_payload=_fixture_payload(title="Candidate B"),
        execution_mode=FIXTURE_EXECUTION_MODE,
    ).to_dict()

    intake_action_for_a = kernel.authorize_followup_evidence_intake()
    intake_result_for_a = execute_followup_evidence_intake_action(
        intake_action_for_a,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    bad_state = deepcopy(intake_result_for_a.record.to_dict())
    bad_state["sealed_candidate_id"] = b_execution["sealed_candidate_id"]
    bad_state["followup_execution_id"] = b_execution["execution_id"]
    bad_state["execution_id"] = b_execution["execution_id"]
    bad_state["followup_execution_observation_id"] = b_execution["observation_id"]
    bad_state["provider_job_kind"] = b_execution["provider_job_kind"]

    bad_observation = Observation.from_action(
        intake_action_for_a,
        observation_type="followup_evidence_intake_observed",
        status="completed",
        payload={"followup_evidence_intake_state": bad_state},
    )
    with pytest.raises(RunKernelTransitionError, match="sealed_candidate_id"):
        kernel.reduce(bad_observation)


def test_intake_authorization_inputs_cannot_override_canonical_binding_fields() -> None:
    kernel = _authorize_and_execute()
    action = kernel.authorize_followup_evidence_intake(
        inputs={
            "execution_id": "malicious-execution",
            "sealed_candidate_id": "auth.candidate.999",
            "provider_job_kind": "semantic_recall",
            "component_id": "component-other",
            "source_obligation_id": "obligation-other",
            "provider_execution_licensed": True,
            "evidence_ledger_intake_mode": "live",
            "caller_note": "preserved_non_binding_input",
        }
    )

    execution = kernel.state.followup_execution_state
    assert action.inputs["execution_id"] == execution["execution_id"]
    assert action.inputs["sealed_candidate_id"] == execution["sealed_candidate_id"]
    assert action.inputs["provider_job_kind"] == execution["provider_job_kind"]
    assert action.inputs["component_id"] == execution["component_id"]
    assert action.inputs["source_obligation_id"] == execution["source_obligation_id"]
    assert action.inputs["requirement_ids"] == execution["requirement_ids"]
    assert action.inputs["provider_execution_licensed"] is False
    assert action.inputs["evidence_ledger_intake_mode"] == FOLLOWUP_EVIDENCE_INTAKE_MODE
    assert action.inputs["caller_note"] == "preserved_non_binding_input"


def test_bridge_only_intake_records_posture_without_satisfying_downstream_surfaces() -> None:
    kernel = _authorize_and_execute(
        fixture_payload=_fixture_payload(bridge_only=True, citation_eligible=True)
    )

    _intake(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert ledger["final_evidence_refs"] == []
    assert kernel.state.followup_evidence_intake_state["bridge_only"] is True
    assert kernel.state.followup_evidence_intake_state["final_evidence_satisfied"] is False
    assert kernel.state.followup_evidence_intake_state["citation_eligible"] is False
    assert kernel.state.final_answer_authority_projection == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"no_result": True},
        {"wrong_source_class": True, "source_class": "reputable_secondary"},
        {"error": "sanitized fixture error"},
    ],
)
def test_failure_status_intake_does_not_create_satisfying_ledger_evidence(
    payload: dict[str, Any],
) -> None:
    kernel = _authorize_and_execute(fixture_payload=_fixture_payload(**payload))

    _intake(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] != SourceRequirementStatus.SATISFIED.value
    assert all(
        record["disposition"] != "accepted"
        for record in ledger["custody_records"]
    )
    assert kernel.state.followup_evidence_intake_state["final_evidence_satisfied"] is False


def test_fixture_success_secondary_source_class_does_not_satisfy_official_current_obligation() -> None:
    kernel = _authorize_and_execute(
        fixture_payload=_fixture_payload(
            source_tier="secondary",
            source_class="reputable_secondary",
            eligible_for_stronger_obligation=True,
        )
    )

    _intake(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    custody = ledger["custody_records"][0]
    assert requirement["required_source_class"] == "official_current_rules"
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert custody["disposition"] == "rejected"
    assert (
        kernel.state.followup_evidence_intake_state[
            "evidence_ledger_candidate_admitted"
        ]
        is False
    )


def test_fixture_success_expected_official_current_source_class_still_intakes_successfully() -> None:
    kernel = _authorize_and_execute(
        fixture_payload=_fixture_payload(source_class="official_government")
    )

    _intake(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["required_source_class"] == "official_current_rules"
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value
    assert ledger["custody_records"][0]["disposition"] == "accepted"


def test_legal_current_primary_provider_job_flows_through_fixture_intake() -> None:
    checkpoint = _checkpoint(
        gaps=[
            _gap(
                GapType.LEGAL_CURRENT_PRIMARY_GAP.value,
                gap_id="gap.legal",
                obligation_id="obligation-legal-current",
                requirement_id="requirement-legal-current",
            )
        ]
    )
    kernel = _authorize_and_execute(
        checkpoint=checkpoint,
        fixture_payload=_fixture_payload(
            source_class="legal_or_regulatory_text",
            source_tier="official",
            title="Current legal text",
        ),
    )

    assert (
        kernel.state.followup_execution_state["provider_job_kind"]
        == "legal_current_primary_acquisition"
    )
    _intake(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_legal_current")
    assert requirement["required_source_class"] == "legal_or_regulatory_text"
    assert requirement["status"] == SourceRequirementStatus.SATISFIED.value


def test_bridge_only_mutated_accepted_ledger_payload_remains_non_satisfying() -> None:
    kernel = _authorize_and_execute(
        fixture_payload=_fixture_payload(bridge_only=True)
    )

    _intake_with_mutated_accepted_ledger_payload(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert ledger["custody_records"][0]["disposition"] == "contextual"
    assert ledger["candidate_records"][0]["final_evidence_eligible"] is False
    assert ledger["final_evidence_refs"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"no_result": True},
        {"wrong_source_class": True, "source_class": "reputable_secondary"},
    ],
)
def test_failure_status_mutated_accepted_ledger_payload_cannot_satisfy(
    payload: dict[str, Any],
) -> None:
    kernel = _authorize_and_execute(fixture_payload=_fixture_payload(**payload))

    _intake_with_mutated_accepted_ledger_payload(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert ledger["custody_records"][0]["disposition"] == "rejected"
    assert ledger["candidate_records"][0]["final_evidence_eligible"] is False
    assert ledger["final_evidence_refs"] == []


def test_secondary_fixture_success_mutated_accepted_ledger_payload_cannot_satisfy() -> None:
    kernel = _authorize_and_execute(
        fixture_payload=_fixture_payload(
            source_tier="secondary",
            source_class="reputable_secondary",
            eligible_for_stronger_obligation=True,
        )
    )

    _intake_with_mutated_accepted_ledger_payload(kernel)

    ledger = kernel.state.evidence_ledger.to_projection().to_dict()
    requirement = _requirement(ledger, "source_requirement:requirement_official_current")
    assert requirement["required_source_class"] == "official_current_rules"
    assert requirement["status"] == SourceRequirementStatus.UNSATISFIED.value
    assert ledger["custody_records"][0]["disposition"] == "rejected"
    assert ledger["candidate_records"][0]["source_class"] == "reputable_secondary"
    assert ledger["candidate_records"][0]["final_evidence_eligible"] is False
    assert ledger["final_evidence_refs"] == []


def test_intake_reducer_rejects_closed_surface_flags() -> None:
    kernel = _authorize_and_execute()
    action = kernel.authorize_followup_evidence_intake()
    result = execute_followup_evidence_intake_action(
        action,
        followup_execution_state=kernel.state.followup_execution_state,
        evidence_ledger_projection=kernel.state.evidence_ledger.to_projection().to_dict(),
    )
    payload = deepcopy(result.record.to_dict())
    payload["behavior_boundary_flags"]["model_called"] = True
    observation = Observation.from_action(
        action,
        observation_type="followup_evidence_intake_observed",
        status="completed",
        payload={"followup_evidence_intake_state": payload},
    )

    with pytest.raises(RunKernelTransitionError, match="model_called=False"):
        kernel.reduce(observation)


def test_intake_does_not_activate_sufficiency_search_final_answer_author_or_citations() -> None:
    kernel = _authorize_and_execute()
    before = {
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "sufficiency_judgment": deepcopy(kernel.state.sufficiency_judgment),
        "sufficiency_judgment_projection": deepcopy(
            kernel.state.sufficiency_judgment_projection
        ),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }

    _intake(kernel)

    assert kernel.state.search_judgment == before["search_judgment"]
    assert kernel.state.search_judgment_projection == before["search_judgment_projection"]
    assert kernel.state.sufficiency_judgment == before["sufficiency_judgment"]
    assert kernel.state.sufficiency_judgment_projection == (
        before["sufficiency_judgment_projection"]
    )
    assert kernel.state.final_answer_packet == before["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == (
        before["final_answer_authority_projection"]
    )
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    flags = kernel.state.followup_evidence_intake_state["behavior_boundary_flags"]
    assert flags["sufficiency_judgment_rechecked"] is False
    assert flags["search_judgment_rerun"] is False
    assert flags["final_answer_packet_updated"] is False
    assert flags["citation_behavior_changed"] is False


def test_static_guards_keep_followup_intake_closed_to_live_surfaces_and_orchestrator() -> None:
    module_paths = [
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
            "FinalAnswerPacket",
            "SufficiencyJudgment",
        ):
            assert token not in source

    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(encoding="utf-8")
    assert "followup_evidence_intake_runtime" not in run_kernel_source
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_evidence_intake_runtime" not in pipeline_source
    assert "FOLLOWUP_EVIDENCE_INTAKE_STAGE" not in pipeline_source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
