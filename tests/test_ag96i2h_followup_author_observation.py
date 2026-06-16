from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest

from core.followup_author_observation_runtime import (
    FOLLOWUP_AUTHOR_OBSERVATION_MODE,
    FOLLOWUP_AUTHOR_OBSERVATION_STAGE,
    execute_followup_author_observation_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.run_kernel import Observation, RunKernel, RunKernelTransitionError
from tests.helpers.followup_fixture_spine import run_followup_fixture_spine

ROOT = Path(__file__).resolve().parents[1]


def _through_packet(
    *,
    packet_mutator: Callable[[RunKernel], None] | None = None,
) -> RunKernel:
    return run_followup_fixture_spine(
        run_id="ag96i2h-fixture",
        packet_mutator=packet_mutator,
    ).kernel


def _ack_refs(refs: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> list[str]:
    acknowledged: list[str] = []
    for ref in refs:
        for key in (
            "requirement_id",
            "source_obligation_id",
            "obligation_id",
            "required_source_class",
            "source_class",
            "reason",
        ):
            value = ref.get(key)
            if value and str(value) not in acknowledged:
                acknowledged.append(str(value))
    return acknowledged


def _compliant_payload(kernel: RunKernel, **overrides: Any) -> dict[str, Any]:
    gate = kernel.state.followup_author_gate_state
    missing_or_partial = list(gate.get("missing_required_obligations", [])) + list(
        gate.get("partial_obligations", [])
    )
    payload = {
        "report_text": "Fixture-only observed answer body. [fixture citation]",
        "citation_source_ids_used": list(gate.get("citation_eligible_source_ids", [])),
        "mandatory_caveats_acknowledged": list(gate.get("mandatory_caveats", [])),
        "prohibited_upgrade_violations": [],
        "source_bound_unknowns_acknowledged": _ack_refs(
            gate.get("source_bound_unknowns", [])
        ),
        "missing_obligations_acknowledged": _ack_refs(missing_or_partial),
        "claim_posture_labels": ["caveated"],
        "refusal_or_caveat_posture": "caveated_fixture_output",
        "fixture_author_notes": ["sanitized fixture note"],
    }
    payload.update(overrides)
    return payload


def _observe(
    kernel: RunKernel,
    payload: Mapping[str, Any] | None = None,
) -> Any:
    action = kernel.authorize_followup_author_observation()
    result = execute_followup_author_observation_action(
        action,
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
        fixture_author_output_payload=payload or _compliant_payload(kernel),
    )
    kernel.reduce(result.observation)
    return action, result


def test_happy_path_observes_fixture_author_output_without_opening_product_answer() -> None:
    kernel = _through_packet()

    _action, result = _observe(kernel)

    state = kernel.state.followup_author_observation_state
    projection = kernel.state.followup_author_observation_projection
    assert state["owner"] == "RunKernel.FollowupAuthorObservation"
    assert state["canonical_state"] is True
    assert projection["trace_only"] is False
    assert projection["author_output_observed"] is True
    assert projection["packet_authority_consumed"] is True
    assert projection["packet_authority_compliance_status"] == "compliant"
    assert projection["author_executor_invoked"] is False
    assert projection["model_called"] is False
    assert projection["final_text_included"] is False
    assert projection["citation_rendering_changed"] is False
    assert projection["citation_formatter_invoked"] is False
    assert projection["product_answer_behavior_changed"] is False
    assert projection["live_validation_not_run"] is True
    assert projection["report_hash"] == result.record.to_dict()["report_hash"]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_OBSERVATION_STAGE] == projection
    assert kernel.state.followup_author_observation_history == [projection]
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    with pytest.raises(RunKernelTransitionError, match="author input payload"):
        kernel.authorize_author_execution()


def test_packet_citation_authority_controls_citation_compliance() -> None:
    kernel = _through_packet()
    allowed = list(kernel.state.followup_author_gate_state["citation_eligible_source_ids"])

    _observe(kernel, _compliant_payload(kernel, citation_source_ids_used=allowed[:1]))

    assert (
        kernel.state.followup_author_observation_state["citation_compliance_status"]
        == "compliant"
    )
    assert (
        kernel.state.followup_author_observation_state[
            "packet_authority_compliance_status"
        ]
        == "compliant"
    )

    kernel = _through_packet()
    payload = _compliant_payload(
        kernel,
        citation_source_ids_used=["unauthorized-source"],
    )
    _observe(kernel, payload)

    state = kernel.state.followup_author_observation_state
    assert state["citation_compliance_status"] == "noncompliant"
    assert state["packet_authority_compliance_status"] == "noncompliant"
    assert state["unauthorized_citation_source_ids"] == ["unauthorized-source"]


def test_packet_mandatory_caveats_and_prohibited_upgrades_control_compliance() -> None:
    kernel = _through_packet()
    payload = _compliant_payload(kernel, mandatory_caveats_acknowledged=[])

    _observe(kernel, payload)

    state = kernel.state.followup_author_observation_state
    assert state["caveat_compliance_status"] == "noncompliant"
    assert state["packet_authority_compliance_status"] == "noncompliant"
    assert "fixture_only_final_answer_packet_author_deferred" in (
        state["missing_mandatory_caveats"]
    )

    kernel = _through_packet()
    payload = _compliant_payload(
        kernel,
        prohibited_upgrade_violations=[
            "do_not_activate_author_from_fixture_only_final_answer_packet"
        ],
    )
    _observe(kernel, payload)

    state = kernel.state.followup_author_observation_state
    assert state["prohibited_upgrade_compliance_status"] == "noncompliant"
    assert state["packet_authority_compliance_status"] == "noncompliant"


def test_source_bound_unknowns_from_packet_must_be_acknowledged() -> None:
    def mutate_packet(kernel: RunKernel) -> None:
        unknown = {
            "requirement_id": "requirement-source-bound-numeric",
            "reason": "source_bound_value_remains_unknown",
        }
        kernel.state.final_answer_packet["source_bound_numeric_unknowns"] = [unknown]

    kernel = _through_packet(packet_mutator=mutate_packet)
    payload = _compliant_payload(kernel, source_bound_unknowns_acknowledged=[])

    _observe(kernel, payload)

    state = kernel.state.followup_author_observation_state
    assert state["source_bound_unknown_compliance_status"] == "noncompliant"
    assert state["packet_authority_compliance_status"] == "noncompliant"
    assert state["unacknowledged_source_bound_unknowns"][0]["requirement_id"] == (
        "requirement-source-bound-numeric"
    )

    kernel = _through_packet(packet_mutator=mutate_packet)
    _observe(kernel)

    assert (
        kernel.state.followup_author_observation_state[
            "source_bound_unknown_compliance_status"
        ]
        == "compliant"
    )


def test_binding_guard_rejects_gate_b_under_gate_a_action() -> None:
    kernel = _through_packet()
    action = kernel.authorize_followup_author_observation()
    result = execute_followup_author_observation_action(
        action,
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
        fixture_author_output_payload=_compliant_payload(kernel),
    )
    kernel.state.followup_author_gate_state["author_gate_id"] = "followup-author-gate:b"

    with pytest.raises(RunKernelTransitionError, match="gate id"):
        kernel.reduce(result.observation)


def test_authorization_inputs_cannot_override_canonical_observation_bindings() -> None:
    kernel = _through_packet()
    action = kernel.authorize_followup_author_observation(
        inputs={
            "packet_id": "malicious-packet",
            "author_gate_id": "malicious-gate",
            "packet_preparation_id": "malicious-packet-prep",
            "recheck_id": "malicious-recheck",
            "intake_id": "malicious-intake",
            "execution_id": "malicious-execution",
            "sealed_candidate_id": "auth.candidate.999",
            "requirement_ids": ["malicious-requirement"],
            "expected_source_classes": ["reputable_secondary"],
            "fixture_author_observation_mode": "live_author_output",
            "author_executor_invoked": True,
            "model_called": True,
            "author_prompt_changed": True,
            "author_prose_behavior_changed": True,
            "citation_rendering_changed": True,
            "citation_formatter_invoked": True,
            "product_answer_behavior_changed": True,
            "final_text_included": True,
            "live_validation_not_run": False,
            "caller_note": "preserved_non_binding_input",
        }
    )
    gate = kernel.state.followup_author_gate_state
    assert action.inputs["packet_id"] == kernel.state.final_answer_packet["packet_id"]
    assert action.inputs["author_gate_id"] == gate["author_gate_id"]
    assert action.inputs["packet_preparation_id"] == gate["packet_preparation_id"]
    assert action.inputs["recheck_id"] == gate["recheck_id"]
    assert action.inputs["intake_id"] == gate["intake_id"]
    assert action.inputs["execution_id"] == gate["execution_id"]
    assert action.inputs["sealed_candidate_id"] == gate["sealed_candidate_id"]
    assert action.inputs["requirement_ids"] == gate["requirement_ids"]
    assert action.inputs["expected_source_classes"] == [
        "official_government",
        "official_current_rules",
    ]
    assert action.inputs["fixture_author_observation_mode"] == (
        FOLLOWUP_AUTHOR_OBSERVATION_MODE
    )
    assert action.inputs["author_executor_invoked"] is False
    assert action.inputs["model_called"] is False
    assert action.inputs["author_prompt_changed"] is False
    assert action.inputs["author_prose_behavior_changed"] is False
    assert action.inputs["citation_rendering_changed"] is False
    assert action.inputs["citation_formatter_invoked"] is False
    assert action.inputs["product_answer_behavior_changed"] is False
    assert action.inputs["final_text_included"] is False
    assert action.inputs["live_validation_not_run"] is True
    assert action.inputs["caller_note"] == "preserved_non_binding_input"


def test_spoofed_compliance_is_overwritten_by_derived_compliance() -> None:
    kernel = _through_packet()
    action = kernel.authorize_followup_author_observation()
    payload = _compliant_payload(
        kernel,
        citation_source_ids_used=["unauthorized-source"],
        mandatory_caveats_acknowledged=[],
    )
    result = execute_followup_author_observation_action(
        action,
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
        fixture_author_output_payload=payload,
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed["packet_authority_compliance_status"] = "compliant"
    observation = Observation.from_action(
        action,
        observation_type="followup_author_observation_observed",
        status="completed",
        payload={"followup_author_observation_state": spoofed},
    )

    kernel.reduce(observation)

    state = kernel.state.followup_author_observation_state
    assert state["packet_authority_compliance_status"] == "noncompliant"
    assert state["citation_compliance_status"] == "noncompliant"
    assert state["caveat_compliance_status"] == "noncompliant"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("author_executor_invoked", True),
        ("model_called", True),
        ("citation_formatter_invoked", True),
        ("product_answer_behavior_changed", True),
        ("final_text_included", True),
        ("live_validation_not_run", False),
    ],
)
def test_boundary_spoofing_is_rejected(field: str, value: bool) -> None:
    kernel = _through_packet()
    action = kernel.authorize_followup_author_observation()
    result = execute_followup_author_observation_action(
        action,
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
        fixture_author_output_payload=_compliant_payload(kernel),
    )
    spoofed = deepcopy(result.record.to_dict())
    spoofed[field] = value
    observation = Observation.from_action(
        action,
        observation_type="followup_author_observation_observed",
        status="completed",
        payload={"followup_author_observation_state": spoofed},
    )

    with pytest.raises(RunKernelTransitionError):
        kernel.reduce(observation)


def test_noncompliant_observation_is_accepted_without_product_activation() -> None:
    kernel = _through_packet()
    payload = _compliant_payload(
        kernel,
        citation_source_ids_used=["outside-packet"],
        mandatory_caveats_acknowledged=[],
    )

    _observe(kernel, payload)

    state = kernel.state.followup_author_observation_state
    assert state["packet_authority_compliance_status"] == "noncompliant"
    assert state["author_output_observed"] is True
    assert state["product_answer_behavior_changed"] is False
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}


def test_closed_surfaces_remain_closed_and_orchestrator_is_untouched() -> None:
    kernel = _through_packet()
    before = {
        "search_judgment": deepcopy(kernel.state.search_judgment),
        "search_judgment_projection": deepcopy(kernel.state.search_judgment_projection),
        "sufficiency_judgment_projection": deepcopy(
            kernel.state.sufficiency_judgment_projection
        ),
        "followup_sufficiency_recheck_state": deepcopy(
            kernel.state.followup_sufficiency_recheck_state
        ),
        "followup_final_answer_packet_state": deepcopy(
            kernel.state.followup_final_answer_packet_state
        ),
        "final_answer_packet": deepcopy(kernel.state.final_answer_packet),
        "author_observation": deepcopy(kernel.state.author_observation),
        "final_answer_outcome": deepcopy(kernel.state.final_answer_outcome),
    }

    _observe(kernel)

    assert kernel.state.search_judgment == before["search_judgment"]
    assert kernel.state.search_judgment_projection == before[
        "search_judgment_projection"
    ]
    assert kernel.state.sufficiency_judgment_projection == before[
        "sufficiency_judgment_projection"
    ]
    assert kernel.state.followup_sufficiency_recheck_state == before[
        "followup_sufficiency_recheck_state"
    ]
    assert kernel.state.followup_final_answer_packet_state == before[
        "followup_final_answer_packet_state"
    ]
    assert kernel.state.final_answer_packet == before["final_answer_packet"]
    assert kernel.state.author_observation == before["author_observation"]
    assert kernel.state.final_answer_outcome == before["final_answer_outcome"]
    flags = kernel.state.followup_author_observation_projection[
        "behavior_boundary_flags"
    ]
    assert flags["author_executor_invoked"] is False
    assert flags["author_prompt_changed"] is False
    assert flags["author_prose_behavior_changed"] is False
    assert flags["citation_formatter_invoked"] is False
    assert flags["product_answer_behavior_changed"] is False
    assert flags["search_judgment_rerun"] is False
    assert flags["sufficiency_judgment_rechecked"] is False
    assert flags["final_answer_packet_rebuilt"] is False
    assert flags["final_answer_packet_updated"] is False

    module_path = ROOT / "core" / "followup_author_observation_runtime.py"
    source = module_path.read_text(encoding="utf-8")
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
    assert passive_module_static_guard(source, module_name=module_path.name) == ()
    assert _imports(module_path).isdisjoint(forbidden_imports)
    for token in (
        "ask_model",
        "select_author_system_prompt",
        "to_author_input_payload",
        "format_citation",
        "execute_author_action",
        "AuthorExecutor",
    ):
        assert token not in source

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "followup_author_observation_runtime" not in pipeline_source
    assert "FOLLOWUP_AUTHOR_OBSERVATION_STAGE" not in pipeline_source


def test_adapter_requires_author_observation_authorized_action_type() -> None:
    kernel = _through_packet()
    wrong_action = kernel.authorize_followup_fixture_execution(
        candidate_id="auth.candidate.001",
        inputs={"fixture_execution_mode": "fixture_only"},
    )

    with pytest.raises(ValueError, match="authorized action type"):
        execute_followup_author_observation_action(
            wrong_action,
            followup_author_gate_state=kernel.state.followup_author_gate_state,
            final_answer_packet=kernel.state.final_answer_packet,
            final_answer_authority_projection=kernel.state.final_answer_authority_projection,
            fixture_author_output_payload=_compliant_payload(kernel),
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
