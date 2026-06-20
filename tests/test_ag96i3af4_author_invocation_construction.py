from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_author_evidence_content_bridge_runtime import (
    ANSWER_BEARING_SANITIZED_EXCERPT,
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS,
    build_followup_author_evidence_content_bridge_record,
)
from core.followup_author_invocation_construction_runtime import (
    AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    AF4_PACKET_MUTATION_FIELDS,
    FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS,
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS,
    FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE,
    build_followup_author_invocation_construction_record,
)
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import Observation, ObservationType, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.test_ag96i3ae_author_execution_from_ad import (
    _kernel_through_ad,
    _stale_ad_action_and_observation,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]
_PREFIXES = (
    "followup_author_payload_construction",
    "followup_author_payload_authority",
    "followup_author_prompt_assembly_manifest",
    "followup_author_execution_activation",
    "followup_author_input_materialization",
    "followup_author_execution_readiness",
    "followup_author_gate",
    "followup_author_input_authority",
    "followup_author_evidence_content_bridge",
    "followup_final_evidence_selection",
    "followup_citation_eligibility",
    "followup_citation_source_handoff",
    "followup_citation_rendering",
)
_CLOSED = (
    "author_input_ready author_execution_allowed author_activation_allowed model_execution_allowed "
    "real_model_called ask_model_called execute_author_action_called author_observation_created "
    "final_answer_outcome_created prompt_text_retained model_response_retained report_text_retained "
    "final_text_retained final_text_included product_answer_ready citation_strings_included "
    "ordered_product_source_output_created"
).split()


def test_af4a_consumes_ad_into_blocked_manifest_model_closed() -> None:
    kernel = _kernel_through_ad()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    ad = deepcopy(kernel.state.followup_author_payload_construction_state)
    upstreams = {
        key: deepcopy(getattr(kernel.state, attr))
        for key, attr in (
            ("ac", "followup_author_payload_authority_state"),
            ("z", "followup_author_prompt_assembly_manifest_state"),
            ("y", "followup_author_execution_activation_state"),
            ("x", "followup_author_input_materialization_state"),
            ("w", "followup_author_execution_readiness_state"),
            ("v1", "followup_author_gate_state"),
            ("u1", "followup_author_input_authority_state"),
        )
    }

    action = kernel.authorize_followup_author_invocation_construction()
    kernel.reduce(_af4_observation(kernel, action))

    state = kernel.state.followup_author_invocation_construction_state
    projection = kernel.state.followup_author_invocation_construction_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    for surface in (packet, authority):
        assert surface["ag96i3_author_invocation_status"] == FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS
        assert surface["ag96i3_author_invocation_content_sufficient"] is False
        for flag in _CLOSED:
            assert surface[flag] is False
        assert surface["author_execution_deferred"] is True
    for surface in (state, projection):
        assert surface["status"] == FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS
        assert surface["author_evidence_content_sufficient"] is False
        for flag in _CLOSED:
            assert surface[flag] is False
        assert surface["author_execution_deferred"] is True
    assert state["missing_author_evidence_content"] == ["answer_bearing_sanitized_excerpt"]
    assert state["missing_author_evidence_content_refs"]
    assert state["source_identity_only_refs"]
    assert state.get("prompt_invocation_digest") is None
    assert state.get("prompt_invocation_length", 0) == 0
    assert state["ad_payload_construction_digest"] == followup_projection_digest(ad)
    for key, upstream in upstreams.items():
        assert state[f"{key}_ad_bound_digest"] == followup_projection_digest(upstream)
    assert packet["author_payload_ref"] == packet_before["author_payload_ref"]
    assert authority["author_payload_ref"] == authority_before["author_payload_ref"]
    assert _changed(packet_before, packet) <= AF4_PACKET_MUTATION_FIELDS
    assert _changed(authority_before, authority) <= AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_author_invocation_construction_history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTION_STAGE] == projection
    trace = kernel.state.to_trace_projection().to_dict()
    assert trace["followup_author_invocation_construction_state"] == state
    assert trace["followup_author_invocation_construction_projection"] == projection
    assert trace["followup_author_invocation_construction_history"] == [projection]


def test_af4c_consumes_af4b2_bridge_into_model_ready_invocation_closed() -> None:
    kernel = _kernel_through_ad()
    _consume_bridge(kernel, _candidate(kernel))
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    bridge_state = deepcopy(kernel.state.followup_author_evidence_content_bridge_state)

    action = kernel.authorize_followup_author_invocation_construction()
    assert action.inputs["status"] == FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS
    assert action.inputs["af4b2_author_evidence_content_bridge_digest"] == (
        bridge_state["content_bridge_digest"]
    )
    kernel.reduce(_af4_observation(kernel, action))

    state = kernel.state.followup_author_invocation_construction_state
    projection = kernel.state.followup_author_invocation_construction_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    for surface in (state, projection):
        assert surface["status"] == FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS
        assert surface["author_evidence_content_sufficient"] is True
        assert surface["author_invocation_constructed"] is True
        assert surface["author_invocation_ready_for_model"] is True
        assert surface["model_execution_allowed"] is False
        assert surface["prompt_text_retained"] is False
        assert surface["author_execution_deferred"] is True
    for surface in (packet, authority):
        assert surface["ag96i3_author_invocation_status"] == (
            FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED_STATUS
        )
        assert surface["ag96i3_author_invocation_content_sufficient"] is True
        assert surface["model_execution_allowed"] is False
    assert state["af4b2_author_evidence_content_bridge_digest"] == (
        bridge_state["content_bridge_digest"]
    )
    assert state["sanitized_author_evidence_content_payload_ref"] == (
        bridge_state["sanitized_author_evidence_content_payload_ref"]
    )
    assert state["sanitized_author_evidence_content_payload_digest"] == (
        bridge_state["sanitized_author_evidence_content_payload_digest"]
    )
    assert state["answer_bearing_sanitized_excerpt_refs"] == (
        bridge_state["answer_bearing_sanitized_excerpt_refs"]
    )
    assert state["invocation_manifest"]["binding_proof"][
        "sanitized_author_evidence_content_payload_digest"
    ] == bridge_state["sanitized_author_evidence_content_payload_digest"]
    assert _changed(packet_before, packet) <= AF4_PACKET_MUTATION_FIELDS
    assert _changed(authority_before, authority) <= (
        AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS
    )
    assert set(state["packet_mutation"]) == AF4_PACKET_MUTATION_FIELDS
    assert set(state["final_answer_authority_projection_mutation"]) == (
        AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS
    )
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert "sanitized_excerpt_text" in repr(bridge_state)
    for surface in (state, projection, packet["ag96i3_author_invocation_ref"]):
        _assert_no_invocation_text_retained(surface)


def test_af4c_invocation_digest_changes_with_af4b2_content_digest() -> None:
    first_digest, first_payload_digest = _af4c_digests_for_text(
        "Bounded sanitized answer-bearing excerpt for Author content custody."
    )
    second_digest, second_payload_digest = _af4c_digests_for_text(
        "Different bounded sanitized answer-bearing excerpt for Author custody."
    )
    assert first_payload_digest != second_payload_digest
    assert first_digest != second_digest


def test_af4c_blocked_af4b2_bridge_remains_missing_content_blocked() -> None:
    kernel = _kernel_through_ad()
    _consume_bridge(kernel)
    assert kernel.state.followup_author_evidence_content_bridge_state["status"] == (
        FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS
    )

    action = kernel.authorize_followup_author_invocation_construction()
    kernel.reduce(_af4_observation(kernel, action))

    state = kernel.state.followup_author_invocation_construction_state
    assert state["status"] == FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS
    assert state["author_evidence_content_bridge_consumed"] is True
    assert state["author_evidence_content_sufficient"] is False
    assert state["author_invocation_ready_for_model"] is False
    assert state["missing_author_evidence_content"] == [
        ANSWER_BEARING_SANITIZED_EXCERPT
    ]
    assert state["missing_author_evidence_content_refs"][0]["reason"] == (
        "af4b2_bridge_blocked_missing_sanitized_excerpt"
    )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda k: k.state.followup_author_evidence_content_bridge_state[
                "sanitized_author_evidence_content_payload"
            ][0].update({"sanitized_excerpt_text": "stale"}),
            "content payload digest",
        ),
        (
            lambda k: k.state.followup_author_evidence_content_bridge_projection.update(
                {"canonical_state": False}
            ),
            "canonical AF4B2 projection",
        ),
        (
            lambda k: k.state.followup_author_evidence_content_bridge_history.clear(),
            "state/projection/history|history",
        ),
        (
            lambda k: k.state.followup_final_evidence_selection_history.clear(),
            "p1 history",
        ),
    ],
)
def test_af4c_rejects_stale_af4b2_bridge_and_bound_inputs(
    mutate: Any,
    match: str,
) -> None:
    kernel = _kernel_through_ad()
    _consume_bridge(kernel, _candidate(kernel))
    action = kernel.authorize_followup_author_invocation_construction()
    observation = _af4_observation(kernel, action)
    mutate(kernel)
    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(observation)
    assert kernel.state.followup_author_invocation_construction_state == {}


def test_af4c_duplicate_stale_upstream_and_output_preexistence_reject() -> None:
    kernel = _kernel_through_ad()
    _consume_bridge(kernel, _candidate(kernel))
    first = kernel.authorize_followup_author_invocation_construction()
    duplicate = kernel.authorize_followup_author_invocation_construction()
    first_observation = _af4_observation(kernel, first)
    duplicate_observation = _af4_observation(kernel, duplicate)
    kernel.reduce(first_observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_invocation_construction()
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AF4"):
        kernel.reduce(duplicate_observation)
    stale_kernel, stale_action, stale_observation = _stale_ad_action_and_observation()
    _, injected = _inject_external_stale_action_and_observation(
        kernel,
        stale_kernel,
        stale_action,
        stale_observation,
    )
    with pytest.raises(RunKernelTransitionError, match="AF4B2|AF4"):
        kernel.reduce(injected)

    for mutate in (
        lambda k: k.state.followup_author_execution_from_ad_state.update({"x": True}),
        lambda k: k.state.author_observation.update({"created": True}),
        lambda k: k.state.final_answer_outcome.update({"created": True}),
    ):
        kernel = _kernel_through_ad()
        _consume_bridge(kernel, _candidate(kernel))
        mutate(kernel)
        with pytest.raises(RunKernelTransitionError, match="AE|Author/final"):
            kernel.authorize_followup_author_invocation_construction()


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "prompt_text",
        "raw_prompt",
        "model_response",
        "final_answer_text",
        "report_text",
        "product_output",
        "raw_provider_payload",
        "provider_payload",
        "db_row",
        "cache",
        "private_log",
        "full_trace",
        "secret",
        "api_key",
    ],
)
def test_af4c_rejects_caller_supplied_closed_fields_recursively(
    forbidden_key: str,
) -> None:
    kernel = _kernel_through_ad()
    with pytest.raises(RunKernelTransitionError, match=forbidden_key):
        kernel.authorize_followup_author_invocation_construction(
            inputs={"nested": {forbidden_key: "closed"}}
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda kernel: kernel.state.followup_author_payload_construction_state.update(status="stale"), "AD payload construction status"),
        (lambda kernel: kernel.state.followup_author_payload_authority_state.update(payload_authority_id="stale"), "ac id"),
        (lambda kernel: kernel.state.followup_author_prompt_assembly_manifest_state.update(author_prompt_assembly_manifest_id="stale"), "z id"),
        (lambda kernel: kernel.state.followup_author_execution_activation_state.update(author_execution_activation_id="stale"), "y id"),
        (lambda kernel: kernel.state.followup_author_input_materialization_state.update(author_input_materialization_id="stale"), "x id"),
        (lambda kernel: kernel.state.followup_author_execution_readiness_state.update(author_execution_readiness_id="stale"), "w id"),
        (lambda kernel: kernel.state.followup_author_gate_state.update(author_gate_id="stale"), "v1 id"),
        (lambda kernel: kernel.state.followup_author_input_authority_state.update(author_input_authority_id="stale"), "u1 id"),
    ],
)
def test_af4a_rejects_stale_ad_bound_inputs(mutate: Any, message: str) -> None:
    kernel = _kernel_through_ad()
    action = kernel.authorize_followup_author_invocation_construction()
    mutate(kernel)
    with pytest.raises((PermissionError, RunKernelTransitionError), match=message):
        _af4_record(kernel, action)


def test_af4a_spoof_duplicate_old_ready_and_stale_reductions_reject_atomically() -> None:
    kernel = _kernel_through_ad()
    with pytest.raises(RunKernelTransitionError, match="prompt_text"):
        kernel.authorize_followup_author_invocation_construction(
            inputs={"prompt_text": "write the answer"}
        )
    kernel.state.final_answer_packet["author_payload_ref"]["status"] = "author_input_ready"
    with pytest.raises(RunKernelTransitionError, match="executable payload status"):
        kernel.authorize_followup_author_invocation_construction()

    kernel = _kernel_through_ad()
    snapshot = _snapshot(kernel)
    action = kernel.authorize_followup_author_invocation_construction()
    observation = _af4_observation(kernel, action)
    observation.payload["followup_author_invocation_construction_state"]["packet_id"] = "spoofed"
    with pytest.raises(RunKernelTransitionError, match="packet_id mismatch"):
        kernel.reduce(observation)
    assert _snapshot(kernel) == snapshot

    kernel.reduce(_af4_observation(kernel, action))
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_invocation_construction()
    stale_kernel, stale_action, stale_observation = _stale_ad_action_and_observation()
    stale_action, stale_observation = _inject_external_stale_action_and_observation(
        kernel,
        stale_kernel,
        stale_action,
        stale_observation,
    )
    with pytest.raises(RunKernelTransitionError, match="stale upstream"):
        kernel.reduce(stale_observation)


def test_af4a_static_guards_and_fast_custody_lane() -> None:
    runtime_path = ROOT / "core" / "followup_author_invocation_construction_runtime.py"
    runtime_imports = imported_modules(runtime_path)
    forbidden_imports = set((
        "core.author_execution_runtime core.runtime_prompt_assembly "
        "core.final_answer_runtime_assembly core.final_answer_runtime_adapter "
        "core.post_author_output_projection core.pipeline_orchestrator core.llm "
        "openai requests httpx urllib dotenv os subprocess"
    ).split()
    )
    assert not runtime_imports & forbidden_imports
    runtime_source = runtime_path.read_text(encoding="utf-8")
    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(encoding="utf-8")
    af4_section = run_kernel_source.split(
        "def authorize_followup_author_invocation_construction",
        1,
    )[1].split("def authorize_followup_author_observation", 1)[0]
    for forbidden in (
        "ask_model(",
        "execute_author_action(",
        "ActionType.AUTHOR_EXECUTE",
        "FinalAnswerAuthorInputPayload",
        "derive_author_input_payload",
        "to_author_input_payload",
    ):
        assert forbidden not in runtime_source
        assert forbidden not in af4_section
    assert (
        "tests/test_ag96i3af4_author_invocation_construction.py::"
        "test_af4a_consumes_ad_into_blocked_manifest_model_closed"
    ) in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert (
        "tests/test_ag96i3af4_author_invocation_construction.py::"
        "test_af4c_consumes_af4b2_bridge_into_model_ready_invocation_closed"
    ) in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def _af4_record(kernel: Any, action: Any) -> dict[str, Any]:
    return build_followup_author_invocation_construction_record(
        action_inputs=action.inputs,
        **_runtime_kwargs(kernel),
    ).to_dict()


def _af4_observation(kernel: Any, action: Any) -> Observation:
    return Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_INVOCATION_CONSTRUCTED,
        status="completed",
        payload={"followup_author_invocation_construction_state": _af4_record(kernel, action)},
    )


def _consume_bridge(kernel: Any, candidate: dict[str, Any] | None = None) -> None:
    if candidate is None:
        action = kernel.authorize_followup_author_evidence_content_bridge()
    else:
        action = kernel.authorize_followup_author_evidence_content_bridge(
            inputs={"sanitized_author_evidence_excerpt_candidates": [candidate]}
        )
    kernel.reduce(_bridge_observation(kernel, action))


def _bridge_observation(kernel: Any, action: Any) -> Observation:
    return Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGED,
        status="completed",
        payload={
            "followup_author_evidence_content_bridge_state": _bridge_record(
                kernel,
                action,
            )
        },
    )


def _bridge_record(kernel: Any, action: Any) -> dict[str, Any]:
    state = kernel.state
    prefixes = (
        "followup_author_payload_construction",
        "followup_author_payload_authority",
        "followup_author_prompt_assembly_manifest",
        "followup_author_execution_activation",
        "followup_author_input_materialization",
        "followup_author_execution_readiness",
        "followup_author_gate",
        "followup_author_input_authority",
        "followup_final_evidence_selection",
        "followup_citation_eligibility",
        "followup_citation_source_handoff",
        "followup_citation_rendering",
    )
    kwargs = {
        f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
        for prefix in prefixes
        for suffix in ("state", "projection", "history")
    }
    kwargs["final_answer_packet"] = state.final_answer_packet
    kwargs["final_answer_authority_projection"] = (
        state.final_answer_authority_projection
    )
    return build_followup_author_evidence_content_bridge_record(
        action_inputs=action.inputs,
        **kwargs,
    ).to_dict()


def _candidate(kernel: Any, *, text: str | None = None) -> dict[str, Any]:
    ref = kernel.state.followup_author_payload_construction_state[
        "allowed_evidence_refs"
    ][0]
    candidate = {
        key: ref[key]
        for key in ("evidence_id", "candidate_id", "source_id")
        if ref.get(key)
    }
    return {
        **candidate,
        "excerpt_ref_id": "excerpt-1",
        "sanitized_excerpt_text": text
        or "Bounded sanitized answer-bearing excerpt for Author content custody.",
        "excerpt_char_limit": 800,
        "content_class": ANSWER_BEARING_SANITIZED_EXCERPT,
        "sanitization_status": "sanitized",
        "evidence_binding_status": "bound_to_ad_authorized_evidence_ref",
        "source_binding_status": "bound_to_ad_authorized_evidence_ref",
    }


def _af4c_digests_for_text(text: str) -> tuple[str, str]:
    kernel = _kernel_through_ad()
    _consume_bridge(kernel, _candidate(kernel, text=text))
    action = kernel.authorize_followup_author_invocation_construction()
    kernel.reduce(_af4_observation(kernel, action))
    state = kernel.state.followup_author_invocation_construction_state
    return (
        state["ag96i3_author_invocation_digest"],
        state["sanitized_author_evidence_content_payload_digest"],
    )


def _assert_no_invocation_text_retained(value: Any) -> None:
    forbidden = set(
        "prompt_text raw_prompt model_response final_answer_text report_text "
        "product_output raw_provider_payload provider_payload db_row cache "
        "private_log full_trace secret api_key sanitized_excerpt_text".split()
    )
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden
            _assert_no_invocation_text_retained(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_invocation_text_retained(child)
    elif isinstance(value, str):
        assert "Bounded sanitized answer-bearing excerpt" not in value


def _runtime_kwargs(kernel: Any) -> dict[str, Any]:
    state = kernel.state
    kwargs = {
        f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
        for prefix in _PREFIXES
        for suffix in ("state", "projection", "history")
    }
    kwargs["final_answer_packet"] = state.final_answer_packet
    kwargs["final_answer_authority_projection"] = state.final_answer_authority_projection
    return kwargs


def _snapshot(kernel: Any) -> dict[str, Any]:
    state = kernel.state
    return {
        "packet": deepcopy(state.final_answer_packet),
        "authority": deepcopy(state.final_answer_authority_projection),
        "af4_state": deepcopy(state.followup_author_invocation_construction_state),
        "af4_projection": deepcopy(state.followup_author_invocation_construction_projection),
        "af4_history": deepcopy(state.followup_author_invocation_construction_history),
        "author_observation": deepcopy(state.author_observation),
        "final_answer_outcome": deepcopy(state.final_answer_outcome),
        "reduced": deepcopy(state.reduced_action_ids),
        "sequence": state.next_observation_sequence,
    }


def _changed(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
