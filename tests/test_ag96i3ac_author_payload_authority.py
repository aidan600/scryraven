from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_author_payload_authority_runtime import (
    AC_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    AC_PACKET_MUTATION_FIELDS,
    AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS,
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE,
    FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS,
    execute_followup_author_payload_authority_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import Observation, RunKernel, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_ac_boundary_snapshot_unchanged,
    assert_no_sensitive_payload,
    snapshot_ac_boundary_state,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)
from tests.test_ag96i3z_author_prompt_assembly_manifest import (
    _consume_z,
    _execute_z,
    _kernel_through_y,
)

ROOT = Path(__file__).resolve().parents[1]


def test_ac_happy_path_consumes_z_and_creates_future_payload_authority() -> None:
    kernel = _kernel_through_z()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    z_state = deepcopy(kernel.state.followup_author_prompt_assembly_manifest_state)
    z_projection = deepcopy(
        kernel.state.followup_author_prompt_assembly_manifest_projection
    )
    y_state = deepcopy(kernel.state.followup_author_execution_activation_state)
    x_state = deepcopy(kernel.state.followup_author_input_materialization_state)
    w_state = deepcopy(kernel.state.followup_author_execution_readiness_state)
    v1_state = deepcopy(kernel.state.followup_author_gate_state)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)

    action = kernel.authorize_followup_author_payload_authority()
    assert action.stage == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE
    assert action.inputs["payload_authority_mode"] == (
        AG96I3AC_Z_CONSUMING_AUTHOR_PAYLOAD_AUTHORITY_MODE
    )
    result = _execute_ac(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_payload_authority_state
    projection = kernel.state.followup_author_payload_authority_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    ref = state["ag96i3_author_payload_authority_ref"]
    for surface in (state, projection):
        assert surface["owner"] == "RunKernel.FollowupAuthorPayloadAuthority"
        assert surface["canonical_state"] is True
        assert surface["status"] == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STATUS
        assert surface["z_author_prompt_assembly_manifest_consumed"] is True
        assert surface["z_author_prompt_assembly_manifest_id"] == (
            z_state["author_prompt_assembly_manifest_id"]
        )
        assert surface["z_author_prompt_assembly_manifest_digest"] == (
            followup_projection_digest(z_state)
        )
        assert surface["z_author_prompt_assembly_manifest_projection_digest"] == (
            followup_projection_digest(z_projection)
        )
        assert surface["y_author_execution_activation_id"] == (
            y_state["author_execution_activation_id"]
        )
        assert surface["y_author_execution_activation_digest"] == (
            followup_projection_digest(y_state)
        )
        assert surface["x_author_input_materialization_id"] == (
            x_state["author_input_materialization_id"]
        )
        assert surface["x_author_input_materialization_digest"] == (
            followup_projection_digest(x_state)
        )
        assert surface["w_author_execution_readiness_id"] == (
            w_state["author_execution_readiness_id"]
        )
        assert surface["v1_author_gate_id"] == v1_state["author_gate_id"]
        assert surface["u1_authority_id"] == u1_state["author_input_authority_id"]
        _assert_x_bill_of_materials(surface["x_bill_of_materials"], x_state)
        _assert_y_demotion(surface)
        _assert_closed_author_surface(surface)

    assert ref["status"] == FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_REF_STATUS
    assert ref["future_author_execution_must_consume"] is True
    assert ref["legacy_author_payload_ref_subordinated"] is True
    assert ref["author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert ref["current_final_answer_packet_digest"] == (
        followup_projection_digest(packet_before)
    )
    assert ref["final_answer_authority_projection_digest"] == (
        followup_projection_digest(authority_before)
    )
    assert packet["ag96i3_author_payload_authority_ref"] == ref
    assert authority["ag96i3_author_payload_authority_ref"] == ref
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    assert kernel.state.followup_author_payload_authority_history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY_STAGE] == (
        projection
    )
    _assert_closed_author_surface(packet)
    _assert_closed_author_surface(authority)
    for surface in (state, projection, ref, packet, authority):
        _assert_no_closed_payload_text(surface)
        assert_no_sensitive_payload(surface)


def test_ac_packet_and_authority_mutation_boundary_is_only_ac_fields() -> None:
    kernel = _kernel_through_z()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    _consume_ac(kernel)

    state = kernel.state.followup_author_payload_authority_state
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    packet_changed = _changed_keys(packet_before, packet)
    authority_changed = _changed_keys(authority_before, authority)
    assert set(state["packet_mutation"]) == set(AC_PACKET_MUTATION_FIELDS)
    assert set(state["final_answer_authority_projection_mutation"]) == set(
        AC_AUTHORITY_PROJECTION_MUTATION_FIELDS
    )
    assert packet_changed <= set(AC_PACKET_MUTATION_FIELDS)
    assert authority_changed <= set(AC_AUTHORITY_PROJECTION_MUTATION_FIELDS)
    assert packet_changed >= {
        "ag96i3_author_payload_authority_ref",
        "ag96i3_author_payload_authority_digest",
        "ag96i3_author_payload_authority_status",
    }
    assert authority_changed >= {
        "ag96i3_author_payload_authority_ref",
        "ag96i3_author_payload_authority_digest",
        "ag96i3_author_payload_authority_status",
    }
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]


@pytest.mark.parametrize(
    ("mutator", "match"),
    [
        (
            lambda kernel: kernel.state.followup_author_prompt_assembly_manifest_state.update(
                {"stale_digest": True}
            ),
            "Z manifest digest|prompt manifest|canonical Z inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_prompt_assembly_manifest_projection.update(
                {"canonical_state": False}
            ),
            "canonical Z",
        ),
        (
            lambda kernel: kernel.state.followup_author_prompt_assembly_manifest_history.clear(),
            "current Z history",
        ),
        (
            lambda kernel: kernel.state.followup_author_execution_activation_state.update(
                {"stale_digest": True}
            ),
            "activation_digest|canonical Z inputs",
        ),
        (
            lambda kernel: kernel.state.followup_author_input_materialization_state.update(
                {"stale_digest": True}
            ),
            "materialization_digest|canonical Z inputs",
        ),
        (
            lambda kernel: kernel.state.final_answer_packet.update(
                {"stale_digest": True}
            ),
            "stale packet|canonical Z inputs",
        ),
        (
            lambda kernel: kernel.state.final_answer_authority_projection.update(
                {"stale_digest": True}
            ),
            "stale authority|canonical Z inputs",
        ),
        (
            lambda kernel: kernel.state.final_answer_packet["author_payload_ref"].update(
                {"status": "author_input_ready"}
            ),
            "deferred|ready|canonical Z inputs",
        ),
    ],
)
def test_ac_missing_stale_or_noncanonical_inputs_reject_atomically(
    mutator: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_z()
    action = kernel.authorize_followup_author_payload_authority()
    result = _execute_ac(kernel, action=action)
    mutator(kernel)
    snapshot = snapshot_ac_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)
    assert_ac_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "payload",
    [
        {"followup_author_payload_authority_state": {"status": "spoofed"}},
        {"ag96i3_author_payload_authority_ref": {"status": "spoofed"}},
        {"prompt_text": "write the answer"},
        {"authority_block_text": "full authority block"},
        {"final_answer_text": "not allowed"},
        {"source_snippet": "raw source text"},
        {"product_output": "ready answer"},
        {"executable_author_input_payload": {"status": "author_input_ready"}},
        {"author_input_ready": True},
    ],
)
def test_ac_caller_supplied_closed_payload_fields_are_rejected(
    payload: dict[str, Any],
) -> None:
    kernel = _kernel_through_z()
    with pytest.raises(
        RunKernelTransitionError,
        match="caller-supplied|retain|requires|ready",
    ):
        kernel.authorize_followup_author_payload_authority(inputs=payload)


def test_ac_spoofed_observation_is_rebuilt_or_rejected_atomically() -> None:
    kernel = _kernel_through_z()
    action = kernel.authorize_followup_author_payload_authority()
    result = _execute_ac(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["ag96i3_author_payload_authority_ref"][
        "payload_authority_ref_id"
    ] = "spoofed-ref"
    spoofed["x_bill_of_materials"]["prompt_or_input_digest"] = "spoofed-digest"
    kernel.reduce(_ac_observation_from_state(action, spoofed))
    state = kernel.state.followup_author_payload_authority_state
    assert state["ag96i3_author_payload_authority_ref"][
        "payload_authority_ref_id"
    ] != "spoofed-ref"
    assert state["x_bill_of_materials"]["prompt_or_input_digest"] != (
        "spoofed-digest"
    )

    kernel = _kernel_through_z()
    action = kernel.authorize_followup_author_payload_authority()
    result = _execute_ac(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["prompt_text"] = "retain this prompt"
    snapshot = snapshot_ac_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="retain"):
        kernel.reduce(_ac_observation_from_state(action, spoofed))
    assert_ac_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _stale_z_action_and_observation(),
    ],
)
def test_ac_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_z()
    _consume_ac(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_ac_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="AG-96I3AC|stale"):
        kernel.reduce(injected_observation)
    assert_ac_boundary_snapshot_unchanged(kernel, snapshot)


def test_ac_duplicate_and_future_execution_guards() -> None:
    kernel = _kernel_through_z()
    first_action = kernel.authorize_followup_author_payload_authority()
    first_result = _execute_ac(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_payload_authority()
    duplicate_result = _execute_ac(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_payload_authority()
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AC"):
        kernel.reduce(duplicate_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)

    kernel.state.final_answer_packet["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    kernel.state.final_answer_authority_projection["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    with pytest.raises(RunKernelTransitionError, match="consume AG-96I3AC"):
        kernel.authorize_author_execution()


def test_ac_static_guards_keep_legacy_execution_product_and_pipeline_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_payload_authority_runtime.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    for path in (runtime_path, run_kernel_path):
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()

    forbidden_imports = {
        "core.runtime_prompt_assembly",
        "core.author_execution_runtime",
        "core.final_answer_runtime_assembly",
        "core.final_answer_runtime_adapter",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "requests",
        "httpx",
        "urllib.request",
        "openai",
        "dotenv",
        "subprocess",
        "os",
    }
    assert imported_modules(runtime_path).isdisjoint(forbidden_imports)
    runtime_source = runtime_path.read_text(encoding="utf-8")
    run_kernel_source = run_kernel_path.read_text(encoding="utf-8")
    ac_sections = [
        run_kernel_source.split("def authorize_followup_author_payload_authority", 1)[
            1
        ].split("def authorize_followup_author_observation", 1)[0],
        run_kernel_source.split(
            "validate_followup_author_payload_authority_observation_binding",
            1,
        )[1].split("self.state.reduced_action_ids.add(action.action_id)", 1)[0],
        run_kernel_source.split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_PAYLOAD_AUTHORITY:",
            1,
        )[1].split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION",
            1,
        )[0],
    ]
    for forbidden in (
        "FinalAnswerAuthorInputPayload",
        "derive_author_input_payload",
        "to_author_input_payload",
        "execute_author_action",
        "ask_model",
        "runtime_prompt_assembly",
        "final_answer_runtime_assembly",
        "pipeline_orchestrator",
        "build_ordered_sources",
    ):
        assert forbidden not in runtime_source
        for section in ac_sections:
            assert forbidden not in section
    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3ac" not in pipeline_source.casefold()
    assert "followup_author_payload_authority" not in pipeline_source


def _kernel_through_z() -> RunKernel:
    kernel = _kernel_through_y()
    _consume_z(kernel)
    return kernel


def _execute_ac(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_payload_authority_action(
        action,
        followup_author_prompt_assembly_manifest_state=(
            kernel.state.followup_author_prompt_assembly_manifest_state
        ),
        followup_author_prompt_assembly_manifest_projection=(
            kernel.state.followup_author_prompt_assembly_manifest_projection
        ),
        followup_author_prompt_assembly_manifest_history=(
            kernel.state.followup_author_prompt_assembly_manifest_history
        ),
        followup_author_execution_activation_state=(
            kernel.state.followup_author_execution_activation_state
        ),
        followup_author_input_materialization_state=(
            kernel.state.followup_author_input_materialization_state
        ),
        followup_author_execution_readiness_state=(
            kernel.state.followup_author_execution_readiness_state
        ),
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        followup_author_input_authority_state=(
            kernel.state.followup_author_input_authority_state
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )


def _consume_ac(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_payload_authority()
    result = _execute_ac(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_z_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_y()
    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    result = _execute_z(kernel, action=action)
    return kernel, action, result.observation


def _ac_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_author_payload_authority_prepared",
        status="completed",
        payload={"followup_author_payload_authority_state": state},
    )


def _changed_keys(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}


def _assert_x_bill_of_materials(bom: dict[str, Any], x_state: dict[str, Any]) -> None:
    for key in (
        "section_ids",
        "section_digests",
        "prompt_or_input_digest",
        "prompt_or_input_length",
        "authority_block_digest",
        "author_payload_ref_digest",
        "rendered_source_entry_digest",
        "source_identity_digest",
    ):
        assert bom[key] == x_state[key]


def _assert_y_demotion(surface: dict[str, Any]) -> None:
    assert surface["y_old_ready_status_demoted"] is True
    assert surface["y_author_input_ready"] is False
    assert surface["activation_consumable_by_future_author_execution"] is True
    assert surface["author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS


def _assert_closed_author_surface(surface: dict[str, Any]) -> None:
    for key in (
        "author_input_ready",
        "author_execution_allowed",
        "author_activation_allowed",
        "prompt_text_retained",
        "authority_block_text_retained",
        "final_answer_author_input_payload_created",
        "final_text_included",
        "product_answer_ready",
        "model_called",
    ):
        if key in surface:
            assert surface[key] is False
    assert surface.get("author_execution_deferred") is True


def _assert_no_closed_payload_text(value: Any) -> None:
    forbidden_keys = {
        "prompt_text",
        "authority_block_text",
        "final_answer_text",
        "answer_text",
        "ordered_sources",
        "ordered_product_source_output",
        "source_snippet",
        "snippet",
        "author_input_payload",
        "executable_author_input_payload",
        "product_output",
        "raw_text",
        "private_payload",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_closed_payload_text(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_closed_payload_text(child)
    elif isinstance(value, str):
        serialized = json.dumps(value).casefold()
        for token in (
            "author_input_ready",
            "z_prompt_manifest",
            "z_authority_block_manifest",
            "write the final markdown report",
            "precision evidence",
        ):
            assert token not in serialized
