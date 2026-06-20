from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from core.followup_author_invocation_construction_runtime import (
    AF4_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    AF4_PACKET_MUTATION_FIELDS,
    FOLLOWUP_AUTHOR_INVOCATION_BLOCKED_MISSING_CONTENT_STATUS,
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
