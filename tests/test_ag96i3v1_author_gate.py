from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_gate_runtime import (
    AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE,
    AG96I3V1_U1_BOUND_AUTHOR_GATE_REASON,
    execute_followup_author_gate_action,
)
from core.followup_author_input_authority_runtime import (
    AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE,
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import (
    FOLLOWUP_AUTHOR_GATE_STAGE,
    Observation,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_no_sensitive_payload,
    assert_v1_boundary_snapshot_unchanged,
    snapshot_v1_boundary_state,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)
from tests.test_ag96i3u1_author_input_authority import (
    _consume_u1,
    _execute_u1,
    _kernel_through_t1,
    _stale_legacy_i2e_action_and_observation,
    _stale_o2_action_and_observation,
    _stale_p1_action_and_observation,
    _stale_q1_action_and_observation,
    _stale_r1_action_and_observation,
    _stale_t1_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v1_happy_path_consumes_u1_authority_without_author_execution() -> None:
    kernel = _kernel_through_u1()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)
    u1_projection = deepcopy(kernel.state.followup_author_input_authority_projection)

    action = kernel.authorize_followup_author_gate()
    assert action.stage == FOLLOWUP_AUTHOR_GATE_STAGE
    assert action.inputs["author_gate_mode"] == AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
    assert action.reason == AG96I3V1_U1_BOUND_AUTHOR_GATE_REASON

    result = _execute_v1(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_gate_state
    projection = kernel.state.followup_author_gate_projection
    assert state["owner"] == "RunKernel.FollowupAuthorGate"
    assert state["canonical_state"] is True
    assert state["author_gate_mode"] == AG96I3V1_U1_BOUND_AUTHOR_GATE_MODE
    assert state["author_input_authority_mode"] == AG96I3U1_AUTHOR_INPUT_AUTHORITY_MODE
    assert projection["owner"] == "RunKernel.FollowupAuthorGate"
    assert projection["canonical_state"] is True
    assert kernel.state.followup_author_gate_history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_GATE_STAGE] == projection

    assert state["packet_authority_consumed"] is True
    assert state["author_input_authority_consumed"] is True
    assert state["author_gate_consumed"] is True
    assert state["author_input_authority_id"] == u1_state["author_input_authority_id"]
    assert state["followup_author_input_authority_digest"] == (
        followup_projection_digest(u1_state)
    )
    assert state["followup_author_input_authority_projection_digest"] == (
        followup_projection_digest(u1_projection)
    )
    assert state["final_answer_authority_projection_digest"] == (
        followup_projection_digest(authority_before)
    )
    assert state["current_final_answer_packet_digest"] == (
        followup_projection_digest(packet_before)
    )
    assert state["author_payload_ref_id"] == packet_before["author_payload_ref"][
        "payload_ref_id"
    ]
    assert state["author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert state["author_input_refs"] == packet_before["author_input_refs"]
    assert state["author_input_refs_digest"] == followup_projection_digest(
        packet_before["author_input_refs"]
    )
    assert state["rendered_source_entry_digest"] == packet_before[
        "author_input_refs"
    ]["rendered_source_entry_digest"]

    assert kernel.state.final_answer_packet == packet_before
    assert kernel.state.final_answer_authority_projection == authority_before
    assert kernel.state.followup_author_input_authority_state == u1_state
    assert kernel.state.followup_author_input_authority_projection == u1_projection
    assert kernel.state.final_answer_packet["author_payload_ref"]["status"] == (
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    )
    _assert_author_and_product_surfaces_closed(kernel)
    with pytest.raises(RunKernelTransitionError, match="packet-ready author input"):
        kernel.authorize_author_execution()


def test_v1_gate_content_is_refs_and_digests_without_product_text() -> None:
    kernel = _kernel_through_u1()
    packet = deepcopy(kernel.state.final_answer_packet)
    authority = deepcopy(kernel.state.final_answer_authority_projection)

    _consume_v1(kernel)

    state = kernel.state.followup_author_gate_state
    projection = kernel.state.followup_author_gate_projection
    for surface in (state, projection):
        assert surface["author_input_authority_id"] == (
            authority["author_input_authority_id"]
        )
        assert surface["packet_id"] == packet["packet_id"]
        assert surface["author_payload_ref_id"] == packet["author_payload_ref"][
            "payload_ref_id"
        ]
        assert surface["author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
        assert surface["author_input_refs_digest"] == followup_projection_digest(
            packet["author_input_refs"]
        )
        assert surface["rendered_source_entry_digest"] == (
            authority["rendered_source_entry_digest"]
        )
        assert surface["author_execution_allowed"] is False
        assert surface["author_activation_allowed"] is False
        assert surface["author_execution_deferred"] is True
        assert surface["prompt_text_included"] is False
        assert surface["final_text_included"] is False
        assert surface["product_answer_ready"] is False
        assert surface["live_validation_not_run"] is True
        _assert_no_product_text_or_private_payload(surface)
        assert_no_sensitive_payload(surface)


@pytest.mark.parametrize(
    ("label", "mutator", "match"),
    [
        (
            "stale U1 digest",
            lambda kernel: kernel.state.followup_author_input_authority_state.update(
                {"stale_digest": True}
            ),
            "U1 authority digest mismatch",
        ),
        (
            "stale final_answer_authority_projection digest",
            lambda kernel: kernel.state.final_answer_authority_projection.update(
                {"stale_digest": True}
            ),
            "final-answer authority|U1 final-answer authority",
        ),
        (
            "stale current packet digest",
            lambda kernel: kernel.state.final_answer_packet.update(
                {"stale_digest": True}
            ),
            "FinalAnswerPacket digest mismatch",
        ),
        (
            "mutated author_payload_ref",
            lambda kernel: kernel.state.final_answer_packet[
                "author_payload_ref"
            ].update({"payload_ref_id": "spoofed-ref"}),
            "payload ref",
        ),
        (
            "mutated author_input_refs",
            lambda kernel: kernel.state.final_answer_packet[
                "author_input_refs"
            ].update({"citation_rendering_id": "spoofed-rendering"}),
            "author_input_refs digest",
        ),
        (
            "missing U1 state",
            lambda kernel: kernel.state.followup_author_input_authority_state.clear(),
            "U1 authority state",
        ),
        (
            "missing U1 projection",
            lambda kernel: kernel.state.followup_author_input_authority_projection.clear(),
            "U1 authority projection",
        ),
        (
            "missing U1 history",
            lambda kernel: kernel.state.followup_author_input_authority_history.clear(),
            "U1 authority history",
        ),
        (
            "noncanonical packet",
            lambda kernel: kernel.state.final_answer_packet.update(
                {"canonical_state": False}
            ),
            "canonical FinalAnswerPacket",
        ),
        (
            "missing final answer authority projection",
            lambda kernel: kernel.state.final_answer_authority_projection.clear(),
            "final-answer authority|final_answer_authority_projection",
        ),
    ],
)
def test_v1_binding_digest_and_currentness_failures_are_atomic(
    label: str,
    mutator: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_u1()
    action = kernel.authorize_followup_author_gate()
    result = _execute_v1(kernel, action=action)
    mutator(kernel)
    snapshot = snapshot_v1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    assert_v1_boundary_snapshot_unchanged(kernel, snapshot), label


def test_v1_observation_spoof_cannot_override_canonical_gate_rebuild() -> None:
    kernel = _kernel_through_u1()
    action = kernel.authorize_followup_author_gate()
    result = _execute_v1(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["rendered_source_entry_refs"] = [{"source_id": "spoofed-source"}]
    spoofed["answer_readiness_posture"] = {"packet_id": "spoofed-packet"}

    kernel.reduce(_v1_observation_from_state(action, spoofed))

    state = kernel.state.followup_author_gate_state
    assert state["rendered_source_entry_refs"] != [{"source_id": "spoofed-source"}]
    assert state["answer_readiness_posture"]["packet_id"] != "spoofed-packet"
    assert state["packet_id"] == kernel.state.final_answer_packet["packet_id"]


def test_v1_malformed_observation_rejects_before_mutation_or_bookkeeping() -> None:
    kernel = _kernel_through_u1()
    action = kernel.authorize_followup_author_gate()
    malformed = Observation.from_action(
        action,
        observation_type="followup_author_gate_observed",
        status="completed",
        payload={},
    )
    snapshot = snapshot_v1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="followup_author_gate_state"):
        kernel.reduce(malformed)

    assert_v1_boundary_snapshot_unchanged(kernel, snapshot)


def test_v1_boundary_spoof_rejects_before_mutation_or_bookkeeping() -> None:
    kernel = _kernel_through_u1()
    action = kernel.authorize_followup_author_gate()
    result = _execute_v1(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["author_execution_allowed"] = True
    snapshot = snapshot_v1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="author_execution_allowed"):
        kernel.reduce(_v1_observation_from_state(action, spoofed))

    assert_v1_boundary_snapshot_unchanged(kernel, snapshot)


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
    ],
)
def test_v1_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_u1()
    _consume_v1(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_v1_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3V1|stale"):
        kernel.reduce(injected_observation)

    assert_v1_boundary_snapshot_unchanged(kernel, snapshot)


def test_v1_duplicate_and_pre_authorized_duplicate_reductions_reject() -> None:
    kernel = _kernel_through_u1()
    first_action = kernel.authorize_followup_author_gate()
    first_result = _execute_v1(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_gate()
    duplicate_result = _execute_v1(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="existing Author gate"):
        kernel.authorize_followup_author_gate()

    snapshot = snapshot_v1_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3V1"):
        kernel.reduce(duplicate_result.observation)
    assert_v1_boundary_snapshot_unchanged(kernel, snapshot)

    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)


def test_v1_static_guards_keep_execution_prompt_product_and_pipeline_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_gate_runtime.py"
    run_kernel_path = ROOT / "core" / "run_kernel.py"
    for path in (runtime_path, run_kernel_path):
        source = path.read_text(encoding="utf-8")
        assert passive_module_static_guard(source, module_name=path.name) == ()

    forbidden_imports = {
        "core.runtime_prompt_assembly",
        "core.author_execution_runtime",
        "core.final_answer_runtime_assembly",
        "core.final_evidence_bundle_builder",
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
    v1_authorize_section = run_kernel_source.split(
        "def _authorize_followup_u1_bound_author_gate",
        1,
    )[1].split("def authorize_followup_author_observation", 1)[0]
    v1_reduce_section = run_kernel_source.split(
        "validate_followup_u1_bound_author_gate_observation_binding",
        1,
    )[1].split(
        "self.state.reduced_action_ids.add(action.action_id)",
        1,
    )[0]
    v1_commit_section = run_kernel_source.split(
        "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_GATE:",
        1,
    )[1].split("elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION", 1)[0]
    for forbidden in (
        "runtime_prompt_assembly",
        "derive_author_input_payload(",
        "build_ordered_sources(",
        "post_author_output_projection(",
        "AuthorExecutor(",
        "AnalystExecutor",
        "EconomistExecutor",
        "execute_author_action(",
    ):
        assert forbidden not in runtime_source
        assert forbidden not in v1_authorize_section
        assert forbidden not in v1_reduce_section
        assert forbidden not in v1_commit_section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3v1" not in pipeline_source.casefold()
    assert "followup_author_gate_runtime" not in pipeline_source


def _kernel_through_u1() -> RunKernel:
    kernel = _kernel_through_t1()
    _consume_u1(kernel)
    return kernel


def _execute_v1(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_gate_action(
        action,
        final_answer_packet=kernel.state.final_answer_packet,
        final_answer_authority_projection=kernel.state.final_answer_authority_projection,
        followup_author_input_authority_state=(
            kernel.state.followup_author_input_authority_state
        ),
        followup_author_input_authority_projection=(
            kernel.state.followup_author_input_authority_projection
        ),
        followup_author_input_authority_history=(
            kernel.state.followup_author_input_authority_history
        ),
    )


def _consume_v1(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_gate()
    result = _execute_v1(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_u1_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_t1()
    action = kernel.authorize_followup_author_input_authority()
    result = _execute_u1(kernel, action=action)
    return kernel, action, result.observation


def _v1_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_author_gate_observed",
        status="completed",
        payload={"followup_author_gate_state": state},
    )


def _assert_author_and_product_surfaces_closed(kernel: RunKernel) -> None:
    packet = kernel.state.final_answer_packet
    state = kernel.state.followup_author_gate_state
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["author_payload_ref"]["status"] != "author_input_ready"
    assert state["author_execution_allowed"] is False
    assert state["author_activation_allowed"] is False
    assert state["author_execution_deferred"] is True
    assert state["prompt_text_included"] is False
    assert state["final_text_included"] is False
    assert state["product_answer_ready"] is False
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}


def _assert_no_product_text_or_private_payload(value: Any) -> None:
    forbidden = {
        "prompt",
        "final_answer_text",
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
        "author_input_payload",
        "analyst_handoff_ref",
        "economist_handoff_ref",
        "raw_text",
        "snippet",
        "snippets",
        "private_payload",
    }
    allowed_false_fields = {
        "prompt_text_included",
        "final_text_included",
        "product_answer_ready",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if key in allowed_false_fields:
                assert child is False
                continue
            assert key not in forbidden
            _assert_no_product_text_or_private_payload(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_product_text_or_private_payload(child)
