from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_author_prompt_assembly_manifest_runtime import (
    AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE,
    FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS,
    Z_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    Z_PACKET_MUTATION_FIELDS,
    execute_followup_author_prompt_assembly_manifest_action,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import Observation, RunKernel, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_no_sensitive_payload,
    assert_z_boundary_snapshot_unchanged,
    snapshot_z_boundary_state,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)
from tests.test_ag96i3u1_author_input_authority import (
    _stale_legacy_i2e_action_and_observation,
    _stale_o2_action_and_observation,
    _stale_p1_action_and_observation,
    _stale_q1_action_and_observation,
    _stale_r1_action_and_observation,
    _stale_t1_action_and_observation,
)
from tests.test_ag96i3v1_author_gate import _stale_u1_action_and_observation
from tests.test_ag96i3w_author_execution_readiness import (
    _stale_v1_action_and_observation,
)
from tests.test_ag96i3x_author_input_materialization import (
    _stale_w_action_and_observation,
)
from tests.test_ag96i3y_author_execution_activation import (
    _consume_y,
    _execute_y,
    _kernel_through_x,
    _stale_x_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_z_happy_path_creates_y_bound_prompt_assembly_manifest() -> None:
    kernel = _kernel_through_y()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    y_state = deepcopy(kernel.state.followup_author_execution_activation_state)
    x_state = deepcopy(kernel.state.followup_author_input_materialization_state)
    w_state = deepcopy(kernel.state.followup_author_execution_readiness_state)
    v1_state = deepcopy(kernel.state.followup_author_gate_state)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)

    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    assert action.stage == FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE
    assert action.inputs["author_prompt_assembly_manifest_mode"] == (
        AG96I3Z_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_MODE
    )

    result = _execute_z(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_prompt_assembly_manifest_state
    projection = kernel.state.followup_author_prompt_assembly_manifest_projection
    manifest_ref = state["author_prompt_assembly_manifest_ref"]
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection

    assert state["owner"] == "RunKernel.FollowupAuthorPromptAssemblyManifest"
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert state["status"] == FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STATUS
    assert projection["owner"] == "RunKernel.FollowupAuthorPromptAssemblyManifest"
    assert projection["canonical_state"] is True
    assert kernel.state.followup_author_prompt_assembly_manifest_history == [
        projection
    ]
    assert (
        kernel.state.projections[FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_STAGE]
        == projection
    )

    assert state["y_author_execution_activation_consumed"] is True
    assert state["x_author_input_materialization_consumed"] is True
    assert state["w_author_execution_readiness_consumed"] is True
    assert state["v1_author_gate_consumed"] is True
    assert state["u1_authority_consumed"] is True
    assert state["packet_authority_consumed"] is True
    assert state["y_author_execution_activation_id"] == (
        y_state["author_execution_activation_id"]
    )
    assert state["y_author_execution_activation_digest"] == (
        followup_projection_digest(y_state)
    )
    assert state["x_author_input_materialization_id"] == (
        x_state["author_input_materialization_id"]
    )
    assert state["x_author_input_materialization_digest"] == (
        followup_projection_digest(x_state)
    )
    assert state["w_author_execution_readiness_id"] == (
        w_state["author_execution_readiness_id"]
    )
    assert state["v1_author_gate_id"] == v1_state["author_gate_id"]
    assert state["u1_authority_id"] == u1_state["author_input_authority_id"]
    assert state["current_final_answer_packet_digest"] == (
        followup_projection_digest(packet_before)
    )
    assert state["final_answer_authority_projection_digest"] == (
        followup_projection_digest(authority_before)
    )

    assert manifest_ref["status"] == FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST_REF_STATUS
    assert manifest_ref["y_author_execution_activation_id"] == (
        y_state["author_execution_activation_id"]
    )
    assert manifest_ref["y_author_execution_activation_digest"] == (
        followup_projection_digest(y_state)
    )
    assert manifest_ref["x_author_input_materialization_id"] == (
        x_state["author_input_materialization_id"]
    )
    assert manifest_ref["w_author_execution_readiness_id"] == (
        w_state["author_execution_readiness_id"]
    )
    assert manifest_ref["v1_author_gate_id"] == v1_state["author_gate_id"]
    assert manifest_ref["u1_authority_id"] == u1_state["author_input_authority_id"]

    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    assert packet["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert packet["author_payload_ref"]["status"] != "author_input_ready"
    assert packet["author_prompt_assembly_manifest_ref"] == manifest_ref
    assert authority["author_prompt_assembly_manifest_ref"] == manifest_ref
    assert packet["author_prompt_assembly_manifest_digest"] == (
        state["author_prompt_assembly_manifest_digest"]
    )
    assert authority["author_prompt_assembly_manifest_digest"] == (
        state["author_prompt_assembly_manifest_digest"]
    )

    _assert_author_and_product_surfaces_closed(kernel)
    with pytest.raises(RunKernelTransitionError, match="packet-ready author input"):
        kernel.authorize_author_execution()


def test_z_manifest_content_is_digests_lengths_and_section_ids_only() -> None:
    kernel = _kernel_through_y()
    packet = deepcopy(kernel.state.final_answer_packet)
    authority = deepcopy(kernel.state.final_answer_authority_projection)
    y_state = deepcopy(kernel.state.followup_author_execution_activation_state)
    x_state = deepcopy(kernel.state.followup_author_input_materialization_state)
    w_state = deepcopy(kernel.state.followup_author_execution_readiness_state)
    v1_state = deepcopy(kernel.state.followup_author_gate_state)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)

    _consume_z(kernel)

    state = kernel.state.followup_author_prompt_assembly_manifest_state
    projection = kernel.state.followup_author_prompt_assembly_manifest_projection
    manifest_ref = state["author_prompt_assembly_manifest_ref"]
    expected_sections = {
        "y_author_execution_activation",
        "y_author_execution_activation_ref",
        "x_author_input_materialization",
        "w_author_execution_readiness",
        "v1_author_gate",
        "u1_authority",
        "final_answer_packet",
        "final_answer_authority_projection",
        "author_input_refs",
        "author_payload_ref",
        "authority_block",
    }
    for surface in (state, projection, manifest_ref):
        assert surface["author_payload_ref_id"] == packet["author_payload_ref"][
            "payload_ref_id"
        ]
        assert surface["author_payload_ref_status"] == (
            FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
        )
        assert surface["current_final_answer_packet_digest"] == (
            followup_projection_digest(packet)
        )
        assert surface["final_answer_authority_projection_digest"] == (
            followup_projection_digest(authority)
        )
        assert surface["author_input_refs_digest"] == followup_projection_digest(
            packet["author_input_refs"]
        )
        assert surface["prompt_text_digest"]
        assert surface["prompt_text_length"] > 0
        assert surface["authority_block_text_digest"]
        assert surface["authority_block_text_length"] > 0
        assert set(surface["prompt_section_ids"]) == expected_sections
        assert set(surface["prompt_section_digests"]) == expected_sections
        assert surface["prompt_section_digests"][
            "y_author_execution_activation"
        ] == followup_projection_digest(y_state)
        assert surface["prompt_section_digests"][
            "x_author_input_materialization"
        ] == followup_projection_digest(x_state)
        assert surface["prompt_section_digests"][
            "w_author_execution_readiness"
        ] == followup_projection_digest(w_state)
        assert surface["prompt_section_digests"]["v1_author_gate"] == (
            followup_projection_digest(v1_state)
        )
        assert surface["prompt_section_digests"]["u1_authority"] == (
            followup_projection_digest(u1_state)
        )
        assert surface["transient_prompt_text_constructed"] is True
        assert surface["transient_authority_block_text_constructed"] is True
        assert surface["prompt_text_retained"] is False
        assert surface["authority_block_text_retained"] is False
        assert surface["prompt_text_included"] is False
        assert surface["final_text_included"] is False
        assert surface["product_answer_ready"] is False
        assert surface["model_called"] is False
        assert surface["live_validation_not_run"] is True
        assert surface["not_for_product_answer_activation"] is True
        _assert_no_prompt_authority_final_source_or_product_text(surface)
        assert_no_sensitive_payload(surface)


def test_z_prompt_and_authority_text_are_not_retained_anywhere() -> None:
    kernel = _kernel_through_y()
    action, result = _consume_z(kernel)
    surfaces = {
        "state": kernel.state.followup_author_prompt_assembly_manifest_state,
        "projection": kernel.state.followup_author_prompt_assembly_manifest_projection,
        "history": kernel.state.followup_author_prompt_assembly_manifest_history,
        "observation_payload": result.observation.payload,
        "packet": kernel.state.final_answer_packet,
        "authority": kernel.state.final_answer_authority_projection,
        "trace": kernel.state.to_trace_projection().to_dict(),
        "action_inputs": action.inputs,
    }
    serialized = json.dumps(surfaces, sort_keys=True)
    assert "z_prompt_manifest" not in serialized
    assert "z_authority_block_manifest" not in serialized
    assert "Write the final markdown report" not in serialized
    assert "FINAL ANSWER PACKET AUTHORITY" not in serialized
    assert "Precision Evidence" not in serialized
    for surface in surfaces.values():
        _assert_no_prompt_authority_final_source_or_product_text(surface)


def test_z_execution_closure_and_ready_status_bypass_prevention() -> None:
    kernel = _kernel_through_y()
    _consume_z(kernel)

    packet = kernel.state.final_answer_packet
    state = kernel.state.followup_author_prompt_assembly_manifest_state
    with pytest.raises(RunKernelTransitionError, match="packet-ready author input"):
        kernel.authorize_author_execution()
    assert packet["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert packet["author_payload_ref"]["status"] != "author_input_ready"
    assert state["author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert state["final_answer_author_input_payload_created"] is False
    assert state["author_input_ready"] is False
    assert state["author_execution_allowed"] is False
    assert state["author_activation_allowed"] is False
    assert state["author_execution_deferred"] is True
    assert state["author_executor_invoked"] is False
    assert state["model_called"] is False

    kernel.state.final_answer_authority_projection["author_payload_ref"][
        "status"
    ] = "author_input_ready"
    with pytest.raises(RunKernelTransitionError, match="AG-96I3 Author execution"):
        kernel.authorize_author_execution()


def test_z_packet_and_authority_projection_mutation_boundary() -> None:
    kernel = _kernel_through_y()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)

    _consume_z(kernel)

    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    packet_changed = {
        key
        for key in set(packet_before) | set(packet)
        if packet_before.get(key) != packet.get(key)
    }
    authority_changed = {
        key
        for key in set(authority_before) | set(authority)
        if authority_before.get(key) != authority.get(key)
    }
    assert packet_changed <= set(Z_PACKET_MUTATION_FIELDS)
    assert authority_changed <= set(Z_AUTHORITY_PROJECTION_MUTATION_FIELDS)
    assert {
        "author_prompt_assembly_manifest_ref",
        "author_prompt_assembly_manifest_ref_created",
        "author_prompt_assembly_manifest_prepared",
        "author_prompt_assembly_manifest_status",
        "author_prompt_assembly_manifest_digest",
    } <= packet_changed
    assert {
        "author_prompt_assembly_manifest_ref",
        "author_prompt_assembly_manifest_ref_created",
        "author_prompt_assembly_manifest_prepared",
        "author_prompt_assembly_manifest_status",
        "author_prompt_assembly_manifest_digest",
    } <= authority_changed
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    for key in set(packet_before) | set(packet):
        if key not in Z_PACKET_MUTATION_FIELDS:
            assert packet.get(key) == packet_before.get(key)
    for key in set(authority_before) | set(authority):
        if key not in Z_AUTHORITY_PROJECTION_MUTATION_FIELDS:
            assert authority.get(key) == authority_before.get(key)


@pytest.mark.parametrize(
    ("label", "mutator", "match"),
    [
        (
            "stale Y digest",
            lambda kernel: kernel.state.followup_author_execution_activation_state.update(
                {"stale_digest": True}
            ),
            "Y digest|Y activation",
        ),
        (
            "stale X digest",
            lambda kernel: kernel.state.followup_author_input_materialization_state.update(
                {"stale_digest": True}
            ),
            "X digest|stale Y X",
        ),
        (
            "stale W digest",
            lambda kernel: kernel.state.followup_author_execution_readiness_state.update(
                {"stale_digest": True}
            ),
            "W digest|stale X W",
        ),
        (
            "stale V1 digest",
            lambda kernel: kernel.state.followup_author_gate_state.update(
                {"stale_digest": True}
            ),
            "V1 digest|stale W V1",
        ),
        (
            "stale U1 digest",
            lambda kernel: kernel.state.followup_author_input_authority_state.update(
                {"stale_digest": True}
            ),
            "U1 digest|stale W U1",
        ),
        (
            "stale final_answer_authority_projection digest",
            lambda kernel: kernel.state.final_answer_authority_projection.update(
                {"stale_digest": True}
            ),
            "final_answer_authority_projection|authority",
        ),
        (
            "stale current FinalAnswerPacket digest",
            lambda kernel: kernel.state.final_answer_packet.update(
                {"stale_digest": True}
            ),
            "FinalAnswerPacket digest",
        ),
        (
            "mutated author_payload_ref",
            lambda kernel: kernel.state.final_answer_packet[
                "author_payload_ref"
            ].update({"payload_ref_id": "spoofed-ref"}),
            "author_payload_ref|payload ref",
        ),
        (
            "mutated author_input_refs",
            lambda kernel: kernel.state.final_answer_packet[
                "author_input_refs"
            ].update({"citation_rendering_id": "spoofed-rendering"}),
            "author_input_refs",
        ),
        (
            "missing Y state",
            lambda kernel: kernel.state.followup_author_execution_activation_state.clear(),
            "Y activation state|activation_state",
        ),
        (
            "noncanonical Y projection",
            lambda kernel: kernel.state.followup_author_execution_activation_projection.update(
                {"canonical_state": False}
            ),
            "canonical Y activation projection",
        ),
        (
            "missing Y history",
            lambda kernel: kernel.state.followup_author_execution_activation_history.clear(),
            "Y activation history",
        ),
        (
            "missing X state",
            lambda kernel: kernel.state.followup_author_input_materialization_state.clear(),
            "X materialization state",
        ),
        (
            "missing W state",
            lambda kernel: kernel.state.followup_author_execution_readiness_state.clear(),
            "W readiness state",
        ),
        (
            "missing V1 state",
            lambda kernel: kernel.state.followup_author_gate_state.clear(),
            "V1 Author gate state",
        ),
        (
            "missing U1 state",
            lambda kernel: kernel.state.followup_author_input_authority_state.clear(),
            "U1 authority state",
        ),
        (
            "missing FinalAnswerPacket",
            lambda kernel: kernel.state.final_answer_packet.clear(),
            "FinalAnswerPacket",
        ),
        (
            "missing final_answer_authority_projection",
            lambda kernel: kernel.state.final_answer_authority_projection.clear(),
            "final_answer_authority_projection",
        ),
    ],
)
def test_z_binding_digest_and_currentness_failures_are_atomic(
    label: str,
    mutator: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_y()
    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    result = _execute_z(kernel, action=action)
    mutator(kernel)
    snapshot = snapshot_z_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    assert_z_boundary_snapshot_unchanged(kernel, snapshot), label


def test_z_spoofed_observation_cannot_override_canonical_rebuild() -> None:
    kernel = _kernel_through_y()
    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    result = _execute_z(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["owner"] = "Caller.SpoofedPromptManifest"
    spoofed["author_prompt_assembly_manifest_ref"][
        "prompt_assembly_manifest_ref_id"
    ] = "spoofed-ref"

    kernel.reduce(_z_observation_from_state(action, spoofed))

    state = kernel.state.followup_author_prompt_assembly_manifest_state
    assert state["owner"] == "RunKernel.FollowupAuthorPromptAssemblyManifest"
    assert state["author_prompt_assembly_manifest_ref"][
        "prompt_assembly_manifest_ref_id"
    ] != "spoofed-ref"


@pytest.mark.parametrize(
    "payload",
    [
        {"followup_author_prompt_assembly_manifest_state": {"status": "spoofed"}},
        {"author_prompt_assembly_manifest_ref": {"status": "spoofed"}},
        {"prompt_text": "write the answer"},
        {"authority_block_text": "full authority block"},
        {"final_answer_text": "not allowed"},
        {"source_snippet": "raw source text"},
        {"formatted_citation": "[1]"},
        {"product_output": "ready answer"},
        {"executable_author_input_payload": {"status": "author_input_ready"}},
        {"author_input_ready": True},
    ],
)
def test_z_caller_supplied_closed_payload_fields_are_rejected(
    payload: dict[str, Any],
) -> None:
    kernel = _kernel_through_y()

    with pytest.raises(
        RunKernelTransitionError,
        match="closed field|caller-supplied|must be false",
    ):
        kernel.authorize_followup_author_prompt_assembly_manifest(inputs=payload)


def test_z_spoofed_closed_observation_rejects_before_bookkeeping() -> None:
    kernel = _kernel_through_y()
    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    result = _execute_z(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["prompt_text"] = "retain this prompt"
    snapshot = snapshot_z_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="closed field"):
        kernel.reduce(_z_observation_from_state(action, spoofed))

    assert_z_boundary_snapshot_unchanged(kernel, snapshot)


def test_z_malformed_observation_rejects_before_mutation_or_bookkeeping() -> None:
    kernel = _kernel_through_y()
    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    malformed = Observation.from_action(
        action,
        observation_type="followup_author_prompt_assembly_manifest_prepared",
        status="completed",
        payload={},
    )
    snapshot = snapshot_z_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="manifest_state"):
        kernel.reduce(malformed)

    assert_z_boundary_snapshot_unchanged(kernel, snapshot)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _stale_legacy_i2e_action_and_observation(),
        lambda: _stale_o2_action_and_observation(),
        lambda: _stale_p1_action_and_observation(),
        lambda: _stale_q1_action_and_observation(),
        lambda: _stale_r1_action_and_observation(),
        lambda: _stale_t1_action_and_observation(),
        lambda: _stale_u1_action_and_observation(),
        lambda: _stale_v1_action_and_observation(),
        lambda: _stale_w_action_and_observation(),
        lambda: _stale_x_action_and_observation(),
        lambda: _stale_y_action_and_observation(),
    ],
)
def test_z_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_y()
    _consume_z(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_z_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3Z|stale"):
        kernel.reduce(injected_observation)

    assert_z_boundary_snapshot_unchanged(kernel, snapshot)


def test_z_duplicate_and_pre_authorized_duplicate_reductions_reject() -> None:
    kernel = _kernel_through_y()
    first_action = kernel.authorize_followup_author_prompt_assembly_manifest()
    first_result = _execute_z(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_prompt_assembly_manifest()
    duplicate_result = _execute_z(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_prompt_assembly_manifest()

    snapshot = snapshot_z_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3Z"):
        kernel.reduce(duplicate_result.observation)
    assert_z_boundary_snapshot_unchanged(kernel, snapshot)

    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)


def test_z_static_guards_keep_payload_execution_product_and_pipeline_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_prompt_assembly_manifest_runtime.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    for path in (runtime_path, run_kernel_path):
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()

    forbidden_imports = {
        "core.runtime_prompt_assembly",
        "core.author_execution_runtime",
        "core.final_answer_runtime_assembly",
        "core.final_evidence_bundle_builder",
        "core.post_author_output_projection",
        "core.pipeline_orchestrator",
        "core.search_providers",
        "core.search_web",
        "core.retrieval_dispatch_runtime",
        "core.retrieval_scheduler",
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
    z_authorize_section = run_kernel_source.split(
        "def authorize_followup_author_prompt_assembly_manifest",
        1,
    )[1].split("def authorize_followup_author_observation", 1)[0]
    z_reduce_section = run_kernel_source.split(
        "validate_followup_author_prompt_assembly_manifest_observation_binding",
        1,
    )[1].split("self.state.reduced_action_ids.add(action.action_id)", 1)[0]
    z_commit_section = run_kernel_source.split(
        "elif (\n            action.action_type\n"
        "            is ActionType.FOLLOWUP_AUTHOR_PROMPT_ASSEMBLY_MANIFEST",
        1,
    )[1].split("elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION", 1)[0]
    for forbidden in (
        "FinalAnswerAuthorInputPayload",
        "derive_author_input_payload",
        "to_author_input_payload",
        "execute_author_action",
        "ask_model",
        "runtime_prompt_assembly",
        "final_answer_runtime_assembly",
        "final_evidence_bundle_builder",
        "post_author_output_projection",
        "pipeline_orchestrator",
        "build_ordered_sources",
        "AuthorExecutor",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in runtime_source
        assert forbidden not in z_authorize_section
        assert forbidden not in z_reduce_section
        assert forbidden not in z_commit_section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3z" not in pipeline_source.casefold()
    assert "followup_author_prompt_assembly_manifest" not in pipeline_source


def _kernel_through_y() -> RunKernel:
    kernel = _kernel_through_x()
    _consume_y(kernel)
    return kernel


def _execute_z(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_prompt_assembly_manifest_action(
        action,
        followup_author_execution_activation_state=(
            kernel.state.followup_author_execution_activation_state
        ),
        followup_author_execution_activation_projection=(
            kernel.state.followup_author_execution_activation_projection
        ),
        followup_author_execution_activation_history=(
            kernel.state.followup_author_execution_activation_history
        ),
        followup_author_input_materialization_state=(
            kernel.state.followup_author_input_materialization_state
        ),
        followup_author_input_materialization_projection=(
            kernel.state.followup_author_input_materialization_projection
        ),
        followup_author_input_materialization_history=(
            kernel.state.followup_author_input_materialization_history
        ),
        followup_author_execution_readiness_state=(
            kernel.state.followup_author_execution_readiness_state
        ),
        followup_author_execution_readiness_projection=(
            kernel.state.followup_author_execution_readiness_projection
        ),
        followup_author_execution_readiness_history=(
            kernel.state.followup_author_execution_readiness_history
        ),
        followup_author_gate_state=kernel.state.followup_author_gate_state,
        followup_author_gate_projection=kernel.state.followup_author_gate_projection,
        followup_author_gate_history=kernel.state.followup_author_gate_history,
        followup_author_input_authority_state=(
            kernel.state.followup_author_input_authority_state
        ),
        followup_author_input_authority_projection=(
            kernel.state.followup_author_input_authority_projection
        ),
        followup_author_input_authority_history=(
            kernel.state.followup_author_input_authority_history
        ),
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
    )


def _consume_z(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_prompt_assembly_manifest()
    result = _execute_z(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_y_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_x()
    action = kernel.authorize_followup_author_execution_activation()
    result = _execute_y(kernel, action=action)
    return kernel, action, result.observation


def _z_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_author_prompt_assembly_manifest_prepared",
        status="completed",
        payload={"followup_author_prompt_assembly_manifest_state": state},
    )


def _assert_author_and_product_surfaces_closed(kernel: RunKernel) -> None:
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    state = kernel.state.followup_author_prompt_assembly_manifest_state
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["product_answer_ready"] is False
    assert packet["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert authority["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert state["author_input_ready"] is False
    assert packet["author_input_ready"] is False
    assert authority["author_input_ready"] is False
    assert state["author_execution_allowed"] is False
    assert packet["author_execution_allowed"] is False
    assert authority["author_execution_allowed"] is False
    assert state["author_activation_allowed"] is False
    assert packet["author_activation_allowed"] is False
    assert authority["author_activation_allowed"] is False
    assert state["author_execution_deferred"] is True
    assert packet["author_execution_deferred"] is True
    assert authority["author_execution_deferred"] is True
    assert state["prompt_text_retained"] is False
    assert packet["prompt_text_retained"] is False
    assert authority["prompt_text_retained"] is False
    assert state["authority_block_text_retained"] is False
    assert packet["authority_block_text_retained"] is False
    assert authority["authority_block_text_retained"] is False
    assert state["final_answer_author_input_payload_created"] is False
    assert state["prompt_text_included"] is False
    assert state["final_text_included"] is False
    assert state["product_answer_ready"] is False
    assert state["model_called"] is False
    assert state["author_executor_invoked"] is False
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}


def _assert_no_prompt_authority_final_source_or_product_text(value: Any) -> None:
    forbidden_keys = {
        "prompt",
        "prompt_text",
        "authority_block_text",
        "final_answer_text",
        "answer_text",
        "ordered_sources",
        "ordered_product_source_output",
        "markdown_source_list",
        "source_list_prose",
        "inline_citation",
        "inline_citation_string",
        "final_answer_citation",
        "final_answer_citation_string",
        "rendered_citation",
        "rendered_citations",
        "formatted_citation",
        "formatted_citations",
        "source_snippet",
        "snippet",
        "snippets",
        "author_input_payload",
        "executable_author_input_payload",
        "product_output",
        "raw_text",
        "private_payload",
    }
    allowed_false_fields = {
        "prompt_text_retained",
        "prompt_text_included",
        "authority_block_text_retained",
        "final_text_included",
        "product_answer_ready",
    }
    allowed_metadata_fields = {
        "prompt_text_digest",
        "prompt_text_length",
        "authority_block_text_digest",
        "authority_block_text_length",
        "prompt_section_ids",
        "prompt_section_digests",
        "transient_prompt_text_constructed",
        "transient_authority_block_text_constructed",
        "author_prompt_assembly_manifest_ref",
        "author_prompt_assembly_manifest_ref_created",
        "author_prompt_assembly_manifest_prepared",
        "author_prompt_assembly_manifest_status",
        "author_prompt_assembly_manifest_digest",
        "author_prompt_assembly_manifest_id",
        "author_prompt_assembly_manifest_mode",
        "author_prompt_assembly_manifest_stage",
        "prompt_assembly_manifest_ref_id",
        "prompt_assembly_manifest_prepared",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if key in allowed_false_fields:
                assert child is False
                continue
            if key in allowed_metadata_fields:
                if key.startswith("transient_"):
                    assert child is True
                continue
            assert key not in forbidden_keys
            if isinstance(child, str):
                lowered = child.casefold()
                assert "author_input_ready" not in lowered
                assert "z_prompt_manifest" not in lowered
                assert "z_authority_block_manifest" not in lowered
                assert "write the final markdown report" not in lowered
            _assert_no_prompt_authority_final_source_or_product_text(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_prompt_authority_final_source_or_product_text(child)
