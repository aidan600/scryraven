from copy import deepcopy
from pathlib import Path

import pytest

import core.followup_author_model_request_assembly_runtime as af4d
from core.run_kernel import ActionType, Observation, ObservationType, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.test_ag96i3ae_author_execution_from_ad import _kernel_through_ad, _stale_ad_action_and_observation
from tests.test_ag96i3af4_author_invocation_construction import _af4_observation, _candidate, _consume_bridge
from tests.test_ag96i3q1_citation_eligibility import _inject_external_stale_action_and_observation

ROOT = Path(__file__).resolve().parents[1]
REQUEST = "What official source supports the current fixture answer?"
FALSE_FLAGS = "model_execution_allowed real_model_called ask_model_called execute_author_action_called author_observation_created final_answer_outcome_created prompt_text_retained model_response_retained report_text_retained final_text_retained product_answer_ready citation_strings_included ordered_product_source_output_created".split()
FORBIDDEN_KEYS = "prompt_text raw_prompt invocation_text model_response final_answer_text report_text product_output".split()
def test_af4d_happy_path_assembles_transient_model_request_model_closed() -> None:
    kernel = _kernel_through_af4c()
    packet_before = deepcopy(kernel.state.final_answer_packet); authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    af4c = deepcopy(kernel.state.followup_author_invocation_construction_state); af4b2 = deepcopy(kernel.state.followup_author_evidence_content_bridge_state)
    action = kernel.authorize_followup_author_model_request_assembly()
    assert action.stage == af4d.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE
    assert action.action_type is ActionType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY
    assert action.expected_observation_type is ObservationType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED
    assert action.inputs["status"] == af4d.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS
    kernel.reduce(_af4d_observation(kernel, action))
    state = kernel.state.followup_author_model_request_assembly_state; projection = kernel.state.followup_author_model_request_assembly_projection
    for surface in (state, projection):
        assert surface["status"] == af4d.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED_STATUS
        assert surface["author_model_request_assembly_mode"] == af4d.AG96I3AF4D_AF4C_BOUND_AUTHOR_MODEL_REQUEST_MODEL_CLOSED_MODE
        assert surface["author_model_request_assembled"] is True and surface["author_model_request_ready_for_execution"] is True
        assert surface["author_model_request_digest"] and surface["author_model_request_length"] > 0 and surface["author_model_request_section_count"] >= 3
        assert surface["af4c_invocation_digest"] == af4c["ag96i3_author_invocation_digest"]
        assert surface["af4b2_bridge_digest"] == af4b2["content_bridge_digest"]
        assert surface["sanitized_author_evidence_content_payload_digest"] == af4b2["sanitized_author_evidence_content_payload_digest"]
        assert surface["answer_bearing_sanitized_excerpt_refs"] == af4b2["answer_bearing_sanitized_excerpt_refs"]
        _assert_closed(surface)
    assert state["binding_proof"]["content_payload_digest_match"] is True and state["bounded_user_request_ref"]["request_text_retained"] is False
    assert kernel.state.final_answer_packet == packet_before and kernel.state.final_answer_authority_projection == authority_before
    assert kernel.state.author_observation == {} and kernel.state.final_answer_outcome == {}
    assert kernel.state.followup_author_model_request_assembly_history == [projection]
    assert kernel.state.projections[af4d.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLY_STAGE] == projection
    trace = kernel.state.to_trace_projection().to_dict()
    assert trace["followup_author_model_request_assembly_state"] == state
    assert trace["followup_author_model_request_assembly_projection"] == projection
    assert trace["followup_author_model_request_assembly_history"] == [projection]
def test_af4d_consumes_af4c_and_af4b2_and_digest_changes_with_excerpt_text() -> None:
    first_request_digest, first_content_digest = _af4d_digests_for_text("Bounded sanitized answer-bearing excerpt for Author content custody.")
    second_request_digest, second_content_digest = _af4d_digests_for_text("Different bounded sanitized answer-bearing excerpt for Author custody.")
    assert first_content_digest != second_content_digest and first_request_digest != second_request_digest
    kernel = _kernel_through_af4c(); action = kernel.authorize_followup_author_model_request_assembly(); kernel.reduce(_af4d_observation(kernel, action))
    state = kernel.state.followup_author_model_request_assembly_state
    assert state["af4c_invocation_digest"] == kernel.state.followup_author_invocation_construction_state["ag96i3_author_invocation_digest"]
    assert state["af4b2_bridge_digest"] == kernel.state.followup_author_evidence_content_bridge_state["content_bridge_digest"]
    assert state["sanitized_author_evidence_content_payload_ref"] == kernel.state.followup_author_evidence_content_bridge_state["sanitized_author_evidence_content_payload_ref"]
    assert state["answer_bearing_sanitized_excerpt_refs"][0]["excerpt_ref_id"] == "excerpt-1"
def test_af4d_retains_no_prompt_model_final_product_or_excerpt_text() -> None:
    kernel = _kernel_through_af4c(); action = kernel.authorize_followup_author_model_request_assembly(); kernel.reduce(_af4d_observation(kernel, action))
    state = kernel.state.followup_author_model_request_assembly_state; projection = kernel.state.followup_author_model_request_assembly_projection
    for surface in (state, projection, kernel.state.followup_author_model_request_assembly_history):
        _assert_absent(surface, FORBIDDEN_KEYS, [REQUEST, "Bounded sanitized answer-bearing excerpt", "Different bounded sanitized answer-bearing excerpt"])
    _assert_absent(projection, ["sanitized_excerpt_text"], [])
def test_af4d_blocks_missing_request_and_rejects_missing_or_blocked_af4c() -> None:
    blocked_request = _kernel_through_af4c(request_text=None); action = blocked_request.authorize_followup_author_model_request_assembly()
    assert action.inputs["status"] == af4d.FOLLOWUP_AUTHOR_MODEL_REQUEST_BLOCKED_STATUS
    blocked_request.reduce(_af4d_observation(blocked_request, action)); state = blocked_request.state.followup_author_model_request_assembly_state
    assert state["author_model_request_assembled"] is False and state["author_model_request_ready_for_execution"] is False
    assert state["missing_model_request_input_classes"] == ["bounded_user_request_text"]
    assert state["model_execution_allowed"] is False and state.get("author_model_request_digest") in (None, "")
    missing = _kernel_through_ad(); missing.state.request = {"query": REQUEST}
    with pytest.raises(RunKernelTransitionError, match="constructed AF4C"):
        missing.authorize_followup_author_model_request_assembly()
    blocked_af4c = _kernel_through_ad(); blocked_af4c.state.request = {"query": REQUEST}; _consume_bridge(blocked_af4c)
    af4 = blocked_af4c.authorize_followup_author_invocation_construction(); blocked_af4c.reduce(_af4_observation(blocked_af4c, af4))
    with pytest.raises(RunKernelTransitionError, match="successful AF4C"):
        blocked_af4c.authorize_followup_author_model_request_assembly()
@pytest.mark.parametrize(("mutate", "match"), [
    (lambda k: k.state.followup_author_invocation_construction_projection.update({"canonical_state": False}), "canonical AF4C"),
    (lambda k: k.state.followup_author_evidence_content_bridge_state["sanitized_author_evidence_content_payload"][0].update({"sanitized_excerpt_text": "stale"}), "content payload digest"),
    (lambda k: k.state.followup_author_payload_construction_history.clear(), "AD history"),
    (lambda k: k.state.followup_author_payload_authority_state.update(payload_authority_id="stale"), "AF4C ac id"),
    (lambda k: k.state.followup_final_evidence_selection_history.clear(), "p1 history"),
])
def test_af4d_rejects_stale_af4c_af4b2_and_bound_inputs(mutate, match) -> None:
    kernel = _kernel_through_af4c(); action = kernel.authorize_followup_author_model_request_assembly(); observation = _af4d_observation(kernel, action); mutate(kernel)
    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(observation)
@pytest.mark.parametrize("forbidden_key", ["prompt_text", "raw_prompt", "invocation_text", "model_response", "final_answer_text", "report_text", "product_output", "output"])
def test_af4d_rejects_caller_supplied_closed_fields_recursively(forbidden_key: str) -> None:
    kernel = _kernel_through_af4c()
    with pytest.raises(RunKernelTransitionError, match=forbidden_key):
        kernel.authorize_followup_author_model_request_assembly(inputs={"nested": {forbidden_key: "closed"}})
def test_af4d_duplicate_stale_upstream_and_output_preexistence_reject() -> None:
    kernel = _kernel_through_af4c()
    first = kernel.authorize_followup_author_model_request_assembly(); duplicate = kernel.authorize_followup_author_model_request_assembly()
    first_observation = _af4d_observation(kernel, first); duplicate_observation = _af4d_observation(kernel, duplicate); kernel.reduce(first_observation)
    with pytest.raises(RunKernelTransitionError, match="already prepared"):
        kernel.authorize_followup_author_model_request_assembly()
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AF4D"):
        kernel.reduce(duplicate_observation)
    stale_kernel, stale_action, stale_observation = _stale_ad_action_and_observation()
    _, injected = _inject_external_stale_action_and_observation(kernel, stale_kernel, stale_action, stale_observation)
    with pytest.raises(RunKernelTransitionError, match="AG-96I3AF4D|stale"):
        kernel.reduce(injected)
    for mutate, match in ((lambda k: k.state.followup_author_execution_from_ad_state.update({"created": True}), "AE"), (lambda k: k.state.author_observation.update({"created": True}), "Author/final"), (lambda k: k.state.final_answer_outcome.update({"created": True}), "Author/final")):
        guarded = _kernel_through_af4c(); mutate(guarded)
        with pytest.raises(RunKernelTransitionError, match=match):
            guarded.authorize_followup_author_model_request_assembly()
def test_af4d_static_guards_and_fast_custody_lane() -> None:
    runtime_path = ROOT / "core" / "followup_author_model_request_assembly_runtime.py"
    forbidden = set("core.author_execution_runtime core.runtime_prompt_assembly core.final_answer_runtime_assembly core.final_answer_runtime_adapter core.post_author_output_projection core.pipeline_orchestrator core.llm openai requests httpx urllib dotenv os subprocess".split())
    assert imported_modules(runtime_path).isdisjoint(forbidden)
    runtime_source = runtime_path.read_text(encoding="utf-8")
    af4d_section = (ROOT / "core" / "run_kernel.py").read_text(encoding="utf-8").split("def authorize_followup_author_model_request_assembly", 1)[1].split("def authorize_followup_author_observation", 1)[0]
    for forbidden_token in ("ask_model(", "execute_author_action(", "ActionType.AUTHOR_EXECUTE", "author_execution_runtime", "runtime_prompt_assembly", "post_author_output_projection", "pipeline_orchestrator", "final_answer_runtime", "build_ordered_sources"):
        assert forbidden_token not in runtime_source and forbidden_token not in af4d_section
    assert "tests/test_ag96i3af4d_author_model_request_assembly.py::test_af4d_happy_path_assembles_transient_model_request_model_closed" in (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
def _kernel_through_af4c(*, request_text: str | None = REQUEST, excerpt_text: str | None = None):
    kernel = _kernel_through_ad(); kernel.state.request = {"query": request_text} if request_text is not None else {}
    _consume_bridge(kernel, _candidate(kernel, text=excerpt_text)); action = kernel.authorize_followup_author_invocation_construction(); kernel.reduce(_af4_observation(kernel, action))
    return kernel
def _af4d_observation(kernel, action) -> Observation:
    return Observation.from_action(action, observation_type=ObservationType.FOLLOWUP_AUTHOR_MODEL_REQUEST_ASSEMBLED, status="completed", payload={"followup_author_model_request_assembly_state": _af4d_record(kernel, action)})
def _af4d_record(kernel, action) -> dict:
    state = kernel.state
    prefixes = "followup_author_payload_construction followup_author_payload_authority followup_author_prompt_assembly_manifest followup_author_execution_activation followup_author_input_materialization followup_author_execution_readiness followup_author_gate followup_author_input_authority followup_author_evidence_content_bridge followup_author_invocation_construction followup_final_evidence_selection followup_citation_eligibility followup_citation_source_handoff followup_citation_rendering".split()
    kwargs = {f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}") for prefix in prefixes for suffix in ("state", "projection", "history")}
    kwargs["run_request"] = state.request
    return af4d.build_followup_author_model_request_assembly_record(action_inputs=action.inputs, **kwargs).to_dict()
def _af4d_digests_for_text(text: str) -> tuple[str, str]:
    kernel = _kernel_through_af4c(excerpt_text=text); action = kernel.authorize_followup_author_model_request_assembly(); kernel.reduce(_af4d_observation(kernel, action))
    state = kernel.state.followup_author_model_request_assembly_state
    return state["author_model_request_digest"], state["sanitized_author_evidence_content_payload_digest"]
def _assert_closed(surface: dict) -> None:
    for flag in FALSE_FLAGS:
        assert surface[flag] is False
    assert surface["author_execution_deferred"] is True
def _assert_absent(value, keys: list[str], text_markers: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in keys; _assert_absent(child, keys, text_markers)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_absent(child, keys, text_markers)
    elif isinstance(value, str):
        for marker in text_markers:
            assert marker not in value
