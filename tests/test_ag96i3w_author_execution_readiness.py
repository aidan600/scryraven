from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_execution_readiness_runtime import (
    AG96I3W_AUTHOR_EXECUTION_READINESS_MODE,
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE,
    FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS,
    execute_followup_author_execution_readiness_action,
)
from core.followup_author_input_authority_runtime import (
    FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS,
)
from core.followup_deliberation_validation import passive_module_static_guard
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import Observation, RunKernel, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.ag96i3_assertions import (
    assert_no_sensitive_payload,
    assert_w_boundary_snapshot_unchanged,
    snapshot_w_boundary_state,
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
from tests.test_ag96i3v1_author_gate import (
    _consume_v1,
    _execute_v1,
    _kernel_through_u1,
    _stale_u1_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_w_happy_path_records_author_execution_readiness_execution_closed() -> None:
    kernel = _kernel_through_v1()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    u1_state = deepcopy(kernel.state.followup_author_input_authority_state)
    u1_projection = deepcopy(kernel.state.followup_author_input_authority_projection)
    v1_state = deepcopy(kernel.state.followup_author_gate_state)
    v1_projection = deepcopy(kernel.state.followup_author_gate_projection)

    action = kernel.authorize_followup_author_execution_readiness()
    assert action.stage == FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE
    assert action.inputs["author_execution_readiness_mode"] == (
        AG96I3W_AUTHOR_EXECUTION_READINESS_MODE
    )

    result = _execute_w(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_execution_readiness_state
    projection = kernel.state.followup_author_execution_readiness_projection
    assert state["owner"] == "RunKernel.FollowupAuthorExecutionReadiness"
    assert state["canonical_state"] is True
    assert state["trace_only"] is False
    assert state["storage_only"] is False
    assert state["status"] == FOLLOWUP_AUTHOR_EXECUTION_READINESS_STATUS
    assert projection["owner"] == "RunKernel.FollowupAuthorExecutionReadiness"
    assert projection["canonical_state"] is True
    assert kernel.state.followup_author_execution_readiness_history == [projection]
    assert (
        kernel.state.projections[FOLLOWUP_AUTHOR_EXECUTION_READINESS_STAGE]
        == projection
    )

    assert state["v1_author_gate_consumed"] is True
    assert state["u1_authority_consumed"] is True
    assert state["packet_authority_consumed"] is True
    assert state["author_execution_readiness_recorded"] is True
    assert state["v1_author_gate_id"] == v1_state["author_gate_id"]
    assert state["v1_author_gate_digest"] == followup_projection_digest(v1_state)
    assert state["v1_author_gate_projection_digest"] == (
        followup_projection_digest(v1_projection)
    )
    assert state["u1_authority_id"] == u1_state["author_input_authority_id"]
    assert state["u1_authority_digest"] == followup_projection_digest(u1_state)
    assert state["u1_authority_projection_digest"] == (
        followup_projection_digest(u1_projection)
    )
    assert state["current_final_answer_packet_digest"] == (
        followup_projection_digest(packet_before)
    )
    assert state["final_answer_authority_projection_digest"] == (
        followup_projection_digest(authority_before)
    )
    assert state["author_input_refs_digest"] == (
        followup_projection_digest(packet_before["author_input_refs"])
    )
    assert state["author_payload_ref_id"] == packet_before["author_payload_ref"][
        "payload_ref_id"
    ]
    assert state["author_payload_ref_status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert state["rendered_source_entry_digest"] == packet_before[
        "author_input_refs"
    ]["rendered_source_entry_digest"]

    assert kernel.state.final_answer_packet == packet_before
    assert kernel.state.final_answer_authority_projection == authority_before
    assert kernel.state.followup_author_input_authority_state == u1_state
    assert kernel.state.followup_author_input_authority_projection == u1_projection
    assert kernel.state.followup_author_gate_state == v1_state
    assert kernel.state.followup_author_gate_projection == v1_projection
    assert packet_before["author_payload_ref"]["status"] == (
        FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    )
    _assert_author_and_product_surfaces_closed(kernel)
    with pytest.raises(RunKernelTransitionError, match="packet-ready author input"):
        kernel.authorize_author_execution()


def test_w_readiness_content_is_refs_and_digests_without_product_text() -> None:
    kernel = _kernel_through_v1()
    packet = deepcopy(kernel.state.final_answer_packet)
    authority = deepcopy(kernel.state.final_answer_authority_projection)

    _consume_w(kernel)

    state = kernel.state.followup_author_execution_readiness_state
    projection = kernel.state.followup_author_execution_readiness_projection
    for surface in (state, projection):
        assert surface["v1_author_gate_id"] == (
            kernel.state.followup_author_gate_state["author_gate_id"]
        )
        assert surface["u1_authority_id"] == authority["author_input_authority_id"]
        assert surface["packet_id"] == packet["packet_id"]
        assert surface["author_payload_ref_id"] == packet["author_payload_ref"][
            "payload_ref_id"
        ]
        assert surface["author_payload_ref_status"] == (
            FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
        )
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
        assert surface["model_called"] is False
        assert surface["live_validation_not_run"] is True
        assert surface["not_for_product_answer_activation"] is True
        _assert_no_product_text_or_private_payload(surface)
        assert_no_sensitive_payload(surface)


def test_w_execution_closure_keeps_author_execution_unauthorizable() -> None:
    kernel = _kernel_through_v1()

    _consume_w(kernel)

    packet = kernel.state.final_answer_packet
    state = kernel.state.followup_author_execution_readiness_state
    with pytest.raises(RunKernelTransitionError, match="packet-ready author input"):
        kernel.authorize_author_execution()
    assert packet["author_payload_ref"]["status"] != "author_input_ready"
    assert state["author_payload_ref_status"] != "author_input_ready"
    assert state["author_execution_allowed"] is False
    assert state["author_activation_allowed"] is False
    assert state["author_execution_deferred"] is True
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}


@pytest.mark.parametrize(
    ("label", "mutator", "match"),
    [
        (
            "stale V1 digest",
            lambda kernel: kernel.state.followup_author_gate_state.update(
                {"stale_digest": True}
            ),
            "V1 Author gate digest|V1.*digest",
        ),
        (
            "stale U1 digest",
            lambda kernel: kernel.state.followup_author_input_authority_state.update(
                {"stale_digest": True}
            ),
            "U1 authority digest|stale U1",
        ),
        (
            "stale final_answer_authority_projection digest",
            lambda kernel: kernel.state.final_answer_authority_projection.update(
                {"stale_digest": True}
            ),
            "final_answer_authority_projection|final-answer authority",
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
            "missing V1 state",
            lambda kernel: kernel.state.followup_author_gate_state.clear(),
            "V1 Author gate state",
        ),
        (
            "noncanonical V1 projection",
            lambda kernel: kernel.state.followup_author_gate_projection.update(
                {"canonical_state": False}
            ),
            "canonical V1 Author gate projection",
        ),
        (
            "missing V1 history",
            lambda kernel: kernel.state.followup_author_gate_history.clear(),
            "V1 Author gate history",
        ),
        (
            "missing U1 state",
            lambda kernel: kernel.state.followup_author_input_authority_state.clear(),
            "U1 authority state",
        ),
        (
            "noncanonical U1 projection",
            lambda kernel: kernel.state.followup_author_input_authority_projection.update(
                {"canonical_state": False}
            ),
            "canonical U1 authority projection",
        ),
        (
            "missing U1 history",
            lambda kernel: kernel.state.followup_author_input_authority_history.clear(),
            "U1 authority history",
        ),
        (
            "missing FinalAnswerPacket",
            lambda kernel: kernel.state.final_answer_packet.clear(),
            "FinalAnswerPacket",
        ),
        (
            "missing final_answer_authority_projection",
            lambda kernel: kernel.state.final_answer_authority_projection.clear(),
            "final-answer authority|final_answer_authority_projection",
        ),
    ],
)
def test_w_binding_digest_and_currentness_failures_are_atomic(
    label: str,
    mutator: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_v1()
    action = kernel.authorize_followup_author_execution_readiness()
    result = _execute_w(kernel, action=action)
    mutator(kernel)
    snapshot = snapshot_w_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)

    assert_w_boundary_snapshot_unchanged(kernel, snapshot), label


def test_w_spoofed_observation_cannot_override_canonical_rebuild() -> None:
    kernel = _kernel_through_v1()
    action = kernel.authorize_followup_author_execution_readiness()
    result = _execute_w(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["packet_readiness_posture"] = {"readiness_status": "spoofed-ready"}
    spoofed["source_identity_digest"] = "spoofed-digest"

    kernel.reduce(_w_observation_from_state(action, spoofed))

    state = kernel.state.followup_author_execution_readiness_state
    assert state["packet_readiness_posture"]["readiness_status"] == "blocked"
    assert state["source_identity_digest"] != "spoofed-digest"


def test_w_caller_supplied_closed_payload_fields_are_rejected() -> None:
    kernel = _kernel_through_v1()

    with pytest.raises(RunKernelTransitionError, match="closed field"):
        kernel.authorize_followup_author_execution_readiness(
            inputs={"prompt_text": "build an Author prompt"}
        )

    action = kernel.authorize_followup_author_execution_readiness()
    result = _execute_w(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["author_output"] = "not allowed"
    snapshot = snapshot_w_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="closed field"):
        kernel.reduce(_w_observation_from_state(action, spoofed))
    assert_w_boundary_snapshot_unchanged(kernel, snapshot)


def test_w_malformed_observation_rejects_before_mutation_or_bookkeeping() -> None:
    kernel = _kernel_through_v1()
    action = kernel.authorize_followup_author_execution_readiness()
    malformed = Observation.from_action(
        action,
        observation_type="followup_author_execution_readiness_prepared",
        status="completed",
        payload={},
    )
    snapshot = snapshot_w_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="readiness_state"):
        kernel.reduce(malformed)

    assert_w_boundary_snapshot_unchanged(kernel, snapshot)


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
    ],
)
def test_w_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Observation]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_v1()
    _consume_w(kernel)
    _, injected_observation = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    snapshot = snapshot_w_boundary_state(kernel)

    with pytest.raises(RunKernelTransitionError, match="AG-96I3W|stale"):
        kernel.reduce(injected_observation)

    assert_w_boundary_snapshot_unchanged(kernel, snapshot)


def test_w_duplicate_and_pre_authorized_duplicate_reductions_reject() -> None:
    kernel = _kernel_through_v1()
    first_action = kernel.authorize_followup_author_execution_readiness()
    first_result = _execute_w(kernel, action=first_action)
    duplicate_action = kernel.authorize_followup_author_execution_readiness()
    duplicate_result = _execute_w(kernel, action=duplicate_action)

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_execution_readiness()

    snapshot = snapshot_w_boundary_state(kernel)
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3W"):
        kernel.reduce(duplicate_result.observation)
    assert_w_boundary_snapshot_unchanged(kernel, snapshot)

    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)


def test_w_static_guards_keep_execution_prompt_product_and_pipeline_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_execution_readiness_runtime.py"
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
    w_authorize_section = run_kernel_source.split(
        "def authorize_followup_author_execution_readiness",
        1,
    )[1].split("def authorize_followup_author_observation", 1)[0]
    w_reduce_section = run_kernel_source.split(
        "validate_followup_author_execution_readiness_observation_binding",
        1,
    )[1].split("self.state.reduced_action_ids.add(action.action_id)", 1)[0]
    w_commit_section = run_kernel_source.split(
        "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_READINESS:",
        1,
    )[1].split("elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION", 1)[0]
    for forbidden in (
        "derive_author_input_payload",
        "build_author_prompt",
        "execute_author_action",
        "ask_model",
        "runtime_prompt_assembly",
        "final_answer_runtime_assembly",
        "final_evidence_bundle_builder",
        "post_author_output_projection",
        "build_ordered_sources",
        "AuthorExecutor",
        "AnalystExecutor",
        "EconomistExecutor",
    ):
        assert forbidden not in runtime_source
        assert forbidden not in w_authorize_section
        assert forbidden not in w_reduce_section
        assert forbidden not in w_commit_section

    pipeline_source = (ROOT / "core" / "pipeline_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "ag96i3w" not in pipeline_source.casefold()
    assert "followup_author_execution_readiness" not in pipeline_source


def _kernel_through_v1() -> RunKernel:
    kernel = _kernel_through_u1()
    _consume_v1(kernel)
    return kernel


def _execute_w(kernel: RunKernel, *, action: Any) -> Any:
    return execute_followup_author_execution_readiness_action(
        action,
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


def _consume_w(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_execution_readiness()
    result = _execute_w(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _stale_v1_action_and_observation() -> tuple[RunKernel, Any, Observation]:
    kernel = _kernel_through_u1()
    action = kernel.authorize_followup_author_gate()
    result = _execute_v1(kernel, action=action)
    return kernel, action, result.observation


def _w_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type="followup_author_execution_readiness_prepared",
        status="completed",
        payload={"followup_author_execution_readiness_state": state},
    )


def _assert_author_and_product_surfaces_closed(kernel: RunKernel) -> None:
    packet = kernel.state.final_answer_packet
    state = kernel.state.followup_author_execution_readiness_state
    assert packet["readiness_status"] == "blocked"
    assert packet["final_answer_allowed"] is False
    assert packet["answer_ready"] is False
    assert packet["product_answer_ready"] is False
    assert packet["author_payload_ref"]["status"] == FOLLOWUP_AUTHOR_PAYLOAD_REF_STATUS
    assert packet["author_payload_ref"]["status"] != "author_input_ready"
    assert state["author_execution_allowed"] is False
    assert state["author_activation_allowed"] is False
    assert state["author_execution_deferred"] is True
    assert state["prompt_text_included"] is False
    assert state["final_text_included"] is False
    assert state["product_answer_ready"] is False
    assert state["model_called"] is False
    assert kernel.state.followup_author_observation_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert getattr(kernel.state, "analyst_author_handoff_state", {}) == {}
    assert getattr(kernel.state, "economist_handoff_state", {}) == {}


def _assert_no_product_text_or_private_payload(value: Any) -> None:
    forbidden = {
        "prompt",
        "prompt_text",
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
        "prose_instruction",
        "style_instruction",
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
