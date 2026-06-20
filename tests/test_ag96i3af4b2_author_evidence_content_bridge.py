from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from core.followup_author_evidence_content_bridge_runtime import (
    AF4B2_AUTHORITY_PROJECTION_MUTATION_FIELDS,
    AF4B2_PACKET_MUTATION_FIELDS,
    ANSWER_BEARING_SANITIZED_EXCERPT,
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS,
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS,
    FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE,
    build_followup_author_evidence_content_bridge_record,
)
from core.followup_final_answer_packet_runtime import followup_projection_digest
from core.run_kernel import Observation, ObservationType, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.test_ag96i3ae_author_execution_from_ad import (
    _consume_ae,
    _kernel_through_ad,
    _stale_ad_action_and_observation,
)
from tests.test_ag96i3af4_author_invocation_construction import _af4_observation
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]
_CLOSED = "author_input_ready author_execution_allowed author_activation_allowed model_execution_allowed real_model_called ask_model_called execute_author_action_called author_observation_created final_answer_outcome_created prompt_text_retained model_response_retained report_text_retained final_text_retained final_text_included product_answer_ready citation_strings_included ordered_product_source_output_created".split()


def test_af4b2_positive_path_binds_sanitized_excerpt_content_model_closed() -> None:
    kernel = _kernel_through_ad()
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    allowed_ref = kernel.state.followup_author_payload_construction_state["allowed_evidence_refs"][0]
    candidate = _candidate(kernel)

    action = _auth(kernel, [candidate])
    kernel.reduce(_bridge_observation(kernel, action))

    state = kernel.state.followup_author_evidence_content_bridge_state
    projection = kernel.state.followup_author_evidence_content_bridge_projection
    packet = kernel.state.final_answer_packet
    authority = kernel.state.final_answer_authority_projection
    for surface in (state, projection, packet, authority):
        assert surface["ag96i3_author_evidence_content_status"] == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BOUND_STATUS
        assert surface["ag96i3_author_evidence_content_sufficient"] is True
        _assert_closed(surface)
    assert state["owner"] == "RunKernel.FollowupAuthorEvidenceContentBridge"
    assert "citation_id" not in candidate
    assert state["sanitized_author_evidence_content_payload"][0]["sanitized_excerpt_text"] == candidate["sanitized_excerpt_text"]
    if allowed_ref.get("citation_id"):
        assert state["sanitized_author_evidence_content_payload"][0]["citation_id"] == allowed_ref["citation_id"]
        assert state["answer_bearing_sanitized_excerpt_refs"][0]["citation_id"] == allowed_ref["citation_id"]
    assert state["answer_bearing_sanitized_excerpt_refs"][0]["excerpt_digest"]
    assert state["ac_ad_bound_digest"] == followup_projection_digest(kernel.state.followup_author_payload_authority_state)
    assert state["u1_ad_bound_digest"] == followup_projection_digest(kernel.state.followup_author_input_authority_state)
    assert state["p1_u1_bound_digest"] == followup_projection_digest(kernel.state.followup_final_evidence_selection_state)
    assert "sanitized_author_evidence_content_payload" not in projection
    assert packet["ag96i3_author_evidence_content_bridge_ref"] == state["content_bridge_ref"]
    assert authority["ag96i3_author_evidence_content_bridge_ref"] == state["content_bridge_ref"]
    assert _changed(packet_before, packet) <= AF4B2_PACKET_MUTATION_FIELDS
    assert _changed(authority_before, authority) <= AF4B2_AUTHORITY_PROJECTION_MUTATION_FIELDS
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_author_invocation_construction_state == {}
    assert kernel.state.followup_author_execution_from_ad_state == {}
    assert kernel.state.followup_author_evidence_content_bridge_history == [projection]
    assert kernel.state.projections[FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGE_STAGE] == projection

    trace = kernel.state.to_trace_projection().to_dict()
    assert trace["followup_author_evidence_content_bridge_state"] == state
    assert trace["followup_author_evidence_content_bridge_projection"] == projection
    assert trace["followup_author_evidence_content_bridge_history"] == [projection]


def test_af4b2_blocked_path_records_missing_sanitized_excerpt_model_closed() -> None:
    kernel = _kernel_through_ad()
    action = _auth(kernel)
    kernel.reduce(_bridge_observation(kernel, action))
    state = kernel.state.followup_author_evidence_content_bridge_state
    assert state["status"] == FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BLOCKED_STATUS
    assert state["missing_author_evidence_content"] == [ANSWER_BEARING_SANITIZED_EXCERPT]
    assert state["author_evidence_content_sufficient"] is False
    assert state["sanitized_author_evidence_content_payload"] == []
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}
    _assert_closed(state)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [(lambda c: c.update({"source_id": "spoofed-source"}), "unbound|spoofed"), (lambda c: c.update({"nested": {"raw_text": "private"}}), "raw_text"), (lambda c: c.update({"sanitized_excerpt_text": "x" * 801}), "over length"), (lambda c: c.update({"excerpt_char_limit": 4}), "exceeds limit")],
)
def test_af4b2_rejects_bad_excerpt_candidates(
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    kernel = _kernel_through_ad()
    candidate = _candidate(kernel)
    mutate(candidate)
    with pytest.raises(RunKernelTransitionError, match=match):
        _auth(kernel, [candidate])


def test_af4b2_rejects_duplicate_excerpt_ref_id() -> None:
    kernel = _kernel_through_ad()
    first = _candidate(kernel, ref_id="dup")
    second = _candidate(kernel, ref_id="dup")
    with pytest.raises(RunKernelTransitionError, match="duplicate excerpt_ref_id"):
        _auth(kernel, [first, second])


def test_af4b2_rejects_caller_supplied_excerpt_digest_proof() -> None:
    kernel = _kernel_through_ad()
    candidate = _candidate(kernel)
    candidate["excerpt_digest"] = "caller-controlled-bogus-digest"
    with pytest.raises(RunKernelTransitionError, match="excerpt_digest"):
        _auth(kernel, [candidate])
    assert kernel.state.followup_author_evidence_content_bridge_state == {}


def test_af4b2_rejects_spoofed_caller_supplied_citation_id_proof() -> None:
    kernel = _kernel_through_ad()
    candidate = _candidate(kernel)
    candidate["citation_id"] = "spoofed-citation"
    with pytest.raises(RunKernelTransitionError, match="citation_id"):
        _auth(kernel, [candidate])
    assert kernel.state.followup_author_evidence_content_bridge_state == {}


@pytest.mark.parametrize(
    ("mutate", "match"),
    [(lambda k: k.state.followup_author_payload_construction_history.clear(), "AD history"), (lambda k: k.state.followup_author_input_authority_state.update(author_input_authority_id="stale"), "u1 id"), (lambda k: k.state.followup_final_evidence_selection_history.clear(), "p1 history")],
)
def test_af4b2_rejects_stale_ad_and_bound_upstreams(
    mutate: Callable[[Any], None],
    match: str,
) -> None:
    kernel = _kernel_through_ad()
    action = _auth(kernel, [_candidate(kernel)])
    observation = _bridge_observation(kernel, action)
    mutate(kernel)
    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(observation)
    assert kernel.state.followup_author_evidence_content_bridge_state == {}


def test_af4b2_duplicate_and_stale_reductions_reject_after_success() -> None:
    kernel = _kernel_through_ad()
    first = _auth(kernel, [_candidate(kernel)])
    duplicate = _auth(kernel, [_candidate(kernel, ref_id="next")])
    first_observation, duplicate_observation = _bridge_observation(kernel, first), _bridge_observation(kernel, duplicate)
    kernel.reduce(first_observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        _auth(kernel)
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AF4B2"):
        kernel.reduce(duplicate_observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_observation)

    stale_kernel, stale_action, stale_observation = _stale_ad_action_and_observation()
    _, injected = _inject_external_stale_action_and_observation(
        kernel,
        stale_kernel,
        stale_action,
        stale_observation,
    )
    with pytest.raises(RunKernelTransitionError, match="AG-96I3AF4B2|stale"):
        kernel.reduce(injected)


@pytest.mark.parametrize(
    "setup",
    [lambda k: k.reduce(_af4_observation(k, k.authorize_followup_author_invocation_construction())), lambda k: _consume_ae(k), lambda k: k.state.author_observation.update({"created": True}), lambda k: k.state.final_answer_outcome.update({"created": True})],
)
def test_af4b2_rejects_when_author_invocation_execution_or_output_exists(
    setup: Callable[[Any], None],
) -> None:
    kernel = _kernel_through_ad()
    setup(kernel)
    with pytest.raises(RunKernelTransitionError, match="AF4a|AE|Author/final"):
        _auth(kernel, [_candidate(kernel)])


def test_af4b2_static_guards_and_fast_custody_lane() -> None:
    runtime_path = ROOT / "core" / "followup_author_evidence_content_bridge_runtime.py"; forbidden = set(
        "core.author_execution_runtime core.runtime_prompt_assembly core.final_answer_runtime_assembly "
        "core.final_answer_runtime_adapter core.post_author_output_projection core.pipeline_orchestrator "
        "core.llm openai requests httpx urllib dotenv os subprocess".split()
    )
    assert imported_modules(runtime_path).isdisjoint(forbidden)
    source = runtime_path.read_text(encoding="utf-8")
    for token in ("ask_model(", "execute_author_action(", "pipeline_orchestrator", "runtime_prompt_assembly"):
        assert token not in source
    assert (
        "tests/test_ag96i3af4b2_author_evidence_content_bridge.py::"
        "test_af4b2_positive_path_binds_sanitized_excerpt_content_model_closed"
    ) in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def _candidate(kernel: Any, *, ref_id: str = "excerpt-1") -> dict[str, Any]:
    ref = kernel.state.followup_author_payload_construction_state["allowed_evidence_refs"][0]
    candidate = {key: ref[key] for key in ("evidence_id", "candidate_id", "source_id") if ref.get(key)}
    return {**candidate, "excerpt_ref_id": ref_id, "sanitized_excerpt_text": "Bounded sanitized answer-bearing excerpt for Author content custody.", "excerpt_char_limit": 800, "content_class": ANSWER_BEARING_SANITIZED_EXCERPT, "sanitization_status": "sanitized", "evidence_binding_status": "bound_to_ad_authorized_evidence_ref", "source_binding_status": "bound_to_ad_authorized_evidence_ref"}


def _auth(kernel: Any, candidates: list[dict[str, Any]] | None = None) -> Any:
    if candidates is None:
        return kernel.authorize_followup_author_evidence_content_bridge()
    return kernel.authorize_followup_author_evidence_content_bridge(
        inputs={"sanitized_author_evidence_excerpt_candidates": candidates}
    )


def _bridge_observation(kernel: Any, action: Any) -> Observation:
    return Observation.from_action(action, observation_type=ObservationType.FOLLOWUP_AUTHOR_EVIDENCE_CONTENT_BRIDGED, status="completed", payload={"followup_author_evidence_content_bridge_state": _record(kernel, action)})


def _record(kernel: Any, action: Any) -> dict[str, Any]:
    state = kernel.state
    prefixes = ("followup_author_payload_construction", "followup_author_payload_authority", "followup_author_prompt_assembly_manifest", "followup_author_execution_activation", "followup_author_input_materialization", "followup_author_execution_readiness", "followup_author_gate", "followup_author_input_authority", "followup_final_evidence_selection", "followup_citation_eligibility", "followup_citation_source_handoff", "followup_citation_rendering")
    kwargs = {f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}") for prefix in prefixes for suffix in ("state", "projection", "history")}
    kwargs["final_answer_packet"] = state.final_answer_packet
    kwargs["final_answer_authority_projection"] = state.final_answer_authority_projection
    return build_followup_author_evidence_content_bridge_record(action_inputs=action.inputs, **kwargs).to_dict()


def _assert_closed(surface: dict[str, Any]) -> None:
    for flag in _CLOSED:
        if flag in surface:
            assert surface[flag] is False
    assert surface["author_execution_deferred"] is True


def _changed(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
