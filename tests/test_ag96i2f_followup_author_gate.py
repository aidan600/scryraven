from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from core.followup_author_gate_runtime import (
    FOLLOWUP_AUTHOR_GATE_MODE,
    execute_followup_author_gate_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_execution_runtime import FIXTURE_EXECUTION_MODE
from core.followup_final_answer_packet_runtime import FOLLOWUP_FINAL_ANSWER_PACKET_MODE
from core.run_kernel import (
    FOLLOWUP_AUTHOR_GATE_STAGE,
    Observation,
    RunKernelTransitionError,
)
from tests.helpers.followup_fixture_spine import (
    consume_followup_author_gate,
    run_followup_through_final_answer_packet,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "ag96i2f-fixture"


def test_happy_path_consumes_packet_into_deferred_author_gate() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)

    _action, result = consume_followup_author_gate(kernel)

    state = kernel.state.followup_author_gate_state
    projection = kernel.state.followup_author_gate_projection
    assert state["owner"] == "RunKernel.FollowupAuthorGate"
    assert state["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["packet_authority_consumed"] is True
    assert projection["author_gate_decision"] == "blocked"
    assert projection["author_gate_reason"] == "packet_final_answer_not_allowed"
    assert projection["author_activation_allowed"] is False
    assert projection["author_execution_deferred"] is True
    assert projection["author_executor_invoked"] is False
    assert projection["final_text_included"] is False
    assert kernel.state.projections[FOLLOWUP_AUTHOR_GATE_STAGE] == projection
    assert kernel.state.followup_author_gate_history == [projection]
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.author_observation == {}
    assert result.record.to_dict()["packet_authority_consumed"] is True
    with pytest.raises(RunKernelTransitionError, match="author input payload"):
        kernel.authorize_author_execution()


def test_gate_consumes_packet_fields_without_reconstructing_from_ledger() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)
    packet_only_citation = {
        "source_id": "packet-only-source",
        "status": "citation_eligible",
        "reason": "packet_only",
    }
    kernel.state.final_answer_packet["mandatory_caveats"] = [
        "packet_only_mandatory_caveat"
    ]
    kernel.state.final_answer_packet["prohibited_upgrades"] = [
        "packet_only_prohibited_upgrade"
    ]
    kernel.state.final_answer_packet["missing_required_obligations"] = [
        {"required_source_class": "packet_missing", "status": "missing"}
    ]
    kernel.state.final_answer_packet["partial_obligations"] = [
        {"required_source_class": "packet_partial", "status": "partial"}
    ]
    kernel.state.final_answer_packet["satisfied_obligations"] = [
        {"required_source_class": "packet_satisfied", "status": "satisfied"}
    ]
    kernel.state.final_answer_packet["source_bound_numeric_unknowns"] = [
        {"requirement_id": "packet-unknown", "reason": "packet_only_unknown"}
    ]
    kernel.state.followup_final_answer_packet_state["unresolved_conflicts"] = [
        "packet_state_unresolved_conflict"
    ]
    kernel.state.followup_final_answer_packet_state["citation_eligibility_refs"] = [
        packet_only_citation
    ]
    kernel.state.final_answer_authority_projection[
        "citation_eligibility_refs"
    ] = [packet_only_citation]
    kernel.state.final_answer_authority_projection[
        "citation_eligible_source_ids"
    ] = ["packet-only-source"]
    kernel.state.final_answer_authority_projection[
        "author_authority_payload_ref"
    ] = {
        "packet_id": kernel.state.final_answer_packet["packet_id"],
        "packet_only_payload": True,
    }

    consume_followup_author_gate(kernel)

    state = kernel.state.followup_author_gate_state
    assert state["mandatory_caveats"] == ["packet_only_mandatory_caveat"]
    assert state["prohibited_upgrades"] == ["packet_only_prohibited_upgrade"]
    assert state["missing_required_obligations"][0]["required_source_class"] == (
        "packet_missing"
    )
    assert state["partial_obligations"][0]["required_source_class"] == (
        "packet_partial"
    )
    assert state["satisfied_obligations"][0]["required_source_class"] == (
        "packet_satisfied"
    )
    assert state["source_bound_unknowns"][0]["requirement_id"] == "packet-unknown"
    assert state["unresolved_conflicts"] == ["packet_state_unresolved_conflict"]
    assert state["citation_eligibility_refs"] == [packet_only_citation]
    assert state["citation_eligible_source_ids"] == ["packet-only-source"]
    assert state["final_answer_authority_payload_ref"]["packet_only_payload"] is True


def test_binding_guard_rejects_packet_b_observation_under_packet_a_action() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)
    action = kernel.authorize_followup_author_gate()
    result = execute_followup_author_gate_action(
        action,
        followup_final_answer_packet_state=kernel.state.followup_final_answer_packet_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )
    bad_state = deepcopy(result.record.to_dict())
    bad_state["packet_id"] = "final-answer-packet-b"
    bad_state["packet_preparation_id"] = "followup-final-answer-packet:b"
    bad_state["followup_final_answer_packet_id"] = "followup-final-answer-packet:b"
    bad_observation = Observation.from_action(
        action,
        observation_type="followup_author_gate_observed",
        status="completed",
        payload={"followup_author_gate_state": bad_state},
    )

    with pytest.raises(RunKernelTransitionError, match="packet"):
        kernel.reduce(bad_observation)


def test_authorization_inputs_cannot_override_canonical_gate_bindings() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)
    action = kernel.authorize_followup_author_gate(
        inputs={
            "packet_id": "malicious-packet",
            "packet_preparation_id": "malicious-packet-prep",
            "followup_final_answer_packet_id": "malicious-followup-packet",
            "recheck_id": "malicious-recheck",
            "intake_id": "malicious-intake",
            "execution_id": "malicious-execution",
            "sealed_candidate_id": "auth.candidate.999",
            "requirement_ids": ["malicious-requirement"],
            "expected_source_classes": ["reputable_secondary"],
            "provider_job_kind": "semantic_recall",
            "component_id": "component-other",
            "source_obligation_id": "obligation-other",
            "author_gate_mode": "live_author_gate",
            "author_activation_allowed": True,
            "author_execution_deferred": False,
            "author_executor_invoked": True,
            "author_prompt_changed": True,
            "author_prose_behavior_changed": True,
            "citation_rendering_changed": True,
            "citation_formatter_invoked": True,
            "product_answer_behavior_changed": True,
            "live_validation_not_run": False,
            "caller_note": "preserved_non_binding_input",
        }
    )
    packet_state = kernel.state.followup_final_answer_packet_state
    assert action.inputs["packet_id"] == kernel.state.final_answer_packet["packet_id"]
    assert action.inputs["packet_preparation_id"] == (
        packet_state["packet_preparation_id"]
    )
    assert action.inputs["followup_final_answer_packet_id"] == (
        packet_state["packet_preparation_id"]
    )
    assert action.inputs["recheck_id"] == packet_state["recheck_id"]
    assert action.inputs["intake_id"] == packet_state["intake_id"]
    assert action.inputs["execution_id"] == packet_state["execution_id"]
    assert action.inputs["sealed_candidate_id"] == packet_state["sealed_candidate_id"]
    assert action.inputs["requirement_ids"] == packet_state["requirement_ids"]
    assert action.inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert action.inputs["provider_job_kind"] == packet_state["provider_job_kind"]
    assert action.inputs["component_id"] == packet_state["component_id"]
    assert action.inputs["source_obligation_id"] == packet_state[
        "source_obligation_id"
    ]
    assert action.inputs["final_answer_packet_mode"] == (
        FOLLOWUP_FINAL_ANSWER_PACKET_MODE
    )
    assert action.inputs["author_gate_mode"] == FOLLOWUP_AUTHOR_GATE_MODE
    assert action.inputs["author_activation_allowed"] is False
    assert action.inputs["author_execution_deferred"] is True
    assert action.inputs["author_executor_invoked"] is False
    assert action.inputs["author_prompt_changed"] is False
    assert action.inputs["author_prose_behavior_changed"] is False
    assert action.inputs["citation_rendering_changed"] is False
    assert action.inputs["citation_formatter_invoked"] is False
    assert action.inputs["product_answer_behavior_changed"] is False
    assert action.inputs["live_validation_not_run"] is True
    assert action.inputs["caller_note"] == "preserved_non_binding_input"


def test_observation_spoofing_is_overwritten_by_canonical_gate_derivation() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)
    action = kernel.authorize_followup_author_gate()
    result = execute_followup_author_gate_action(
        action,
        followup_final_answer_packet_state=kernel.state.followup_final_answer_packet_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed["author_activation_allowed"] = True
    spoofed["author_execution_deferred"] = False
    spoofed["author_executor_invoked"] = True
    spoofed["final_text_included"] = True
    spoofed["product_answer_behavior_changed"] = True
    spoofed["citation_formatter_invoked"] = True
    spoofed["mandatory_caveats"] = []
    spoofed["prohibited_upgrades"] = []
    spoofed["packet_authority_consumed"] = False
    spoofed["behavior_boundary_flags"]["author_executor_invoked"] = True
    observation = Observation.from_action(
        action,
        observation_type="followup_author_gate_observed",
        status="completed",
        payload={"followup_author_gate_state": spoofed},
    )

    kernel.reduce(observation)

    state = kernel.state.followup_author_gate_state
    assert state["author_activation_allowed"] is False
    assert state["author_execution_deferred"] is True
    assert state["author_executor_invoked"] is False
    assert state["final_text_included"] is False
    assert state["product_answer_behavior_changed"] is False
    assert state["citation_formatter_invoked"] is False
    assert "fixture_only_final_answer_packet_author_deferred" in (
        state["mandatory_caveats"]
    )
    assert "do_not_activate_author_from_fixture_only_final_answer_packet" in (
        state["prohibited_upgrades"]
    )
    assert state["packet_authority_consumed"] is True
    assert state["behavior_boundary_flags"]["author_executor_invoked"] is False


def test_closed_surfaces_remain_closed_and_orchestrator_is_untouched() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)
    before = {
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "final_answer_authority_projection": deepcopy(
            kernel.state.final_answer_authority_projection
        ),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }

    consume_followup_author_gate(kernel)

    assert kernel.state.final_answer_packet == before["final_answer_packet"]
    assert kernel.state.final_answer_authority_projection == before[
        "final_answer_authority_projection"
    ]
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    flags = kernel.state.followup_author_gate_projection["behavior_boundary_flags"]
    assert flags["author_executor_invoked"] is False
    assert flags["author_prompt_changed"] is False
    assert flags["author_prose_behavior_changed"] is False
    assert flags["citation_formatter_invoked"] is False
    assert flags["product_answer_behavior_changed"] is False
    assert flags["final_answer_packet_rebuilt"] is False

    module_paths = [
        ROOT / "core" / "followup_author_gate_runtime.py",
        ROOT / "core" / "followup_final_answer_packet_runtime.py",
    ]
    forbidden_imports = {
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
        "core.pipeline_orchestrator",
        "core.author_execution_runtime",
        "subprocess",
        "os",
        "requests",
        "openai",
    }
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()
        assert _imports(path).isdisjoint(forbidden_imports)
    gate_source = (ROOT / "core" / "followup_author_gate_runtime.py").read_text(
        encoding="utf-8"
    )
    for token in (
        "ask_model",
        "select_author_system_prompt",
        "to_author_input_payload",
        "format_citation",
        "execute_author_action",
        "AuthorExecutor",
    ):
        assert token not in gate_source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_author_gate_runtime" not in pipeline_source
    assert "FOLLOWUP_AUTHOR_GATE_STAGE" not in pipeline_source


def test_adapter_requires_author_gate_authorized_action_type() -> None:
    kernel = run_followup_through_final_answer_packet(run_id=RUN_ID)
    wrong_action = kernel.authorize_followup_fixture_execution(
        candidate_id="auth.candidate.001",
        inputs={"fixture_execution_mode": FIXTURE_EXECUTION_MODE},
    )

    with pytest.raises(ValueError, match="authorized action type"):
        execute_followup_author_gate_action(
            wrong_action,
            followup_final_answer_packet_state=kernel.state.followup_final_answer_packet_state,
            final_answer_packet=kernel.state.final_answer_packet,
            final_answer_authority_projection=kernel.state.final_answer_authority_projection,
        )


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
