from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

import core.followup_author_response_finalization_runtime as af5b
from core.run_kernel import (
    ActionType,
    Observation,
    ObservationType,
    RunKernel,
    RunKernelTransitionError,
)
from tests.ag96_static_guards import imported_modules
from tests.test_ag96i3af5a_author_execution_from_af4d import (
    FakeAF5AAdapter,
    MockLiveAF5AAdapter,
    _execute_af5a,
    _kernel_through_af4d,
)

ROOT = Path(__file__).resolve().parents[1]
ANSWER_TEXT = "AF5B product answer exists from the bounded AF5A fake-adapter candidate."
FAKE_MODEL_CALL_CUSTODY = {
    "author_model_call_mode": "fake",
    "author_model_call_status": "completed_fake",
    "author_model_call_source": "injected_fake_model_adapter",
    "max_model_calls": 0,
    "model_calls_used": 0,
    "mock_model_adapter_calls_used": 0,
    "live_model_call_performed": False,
    "live_adapter_mocked": False,
    "fake_adapter_used": True,
    "broker_live_adapter_deferred": False,
    "broker_live_requested": False,
    "broker_live_execution_enabled": False,
    "prompt_raw_payload_retained": False,
    "model_request_raw_payload_retained": False,
    "provider_raw_payload_retained": False,
    "payload_raw_retained": False,
    "model_response_raw_payload_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}
MOCK_LIVE_MODEL_CALL_CUSTODY = {
    "author_model_call_mode": "live_adapter_mocked",
    "author_model_call_status": "completed_mock_live_adapter",
    "author_model_call_source": "mock_live_model_adapter",
    "max_model_calls": 0,
    "model_calls_used": 0,
    "mock_model_adapter_calls_used": 1,
    "live_model_call_performed": False,
    "live_adapter_mocked": True,
    "fake_adapter_used": False,
    "broker_live_adapter_deferred": False,
    "broker_live_requested": False,
    "broker_live_execution_enabled": False,
    "prompt_raw_payload_retained": False,
    "model_request_raw_payload_retained": False,
    "provider_raw_payload_retained": False,
    "payload_raw_retained": False,
    "model_response_raw_payload_retained": False,
    "private_logs_retained": False,
    "db_cache_rows_retained": False,
    "full_trace_retained": False,
}


def test_af5b_converts_af5a_fake_adapter_candidate_to_product_answer_text() -> None:
    kernel = _kernel_through_af4d()
    _consume_af5a_with_text(kernel, ANSWER_TEXT)
    packet_before = deepcopy(kernel.state.final_answer_packet)
    authority_before = deepcopy(kernel.state.final_answer_authority_projection)
    af5a_state = deepcopy(kernel.state.followup_author_execution_from_af4d_state)

    action = kernel.authorize_followup_author_response_finalization()
    assert action.stage == af5b.FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE
    assert action.action_type is ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE
    assert action.expected_observation_type is (ObservationType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZED)
    assert action.inputs["af5a_author_response_candidate_digest"] == (af5a_state["author_response_candidate_digest"])
    assert action.inputs["followup_author_execution_from_ad_consumed"] is False

    result = _execute_af5b(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_response_finalization_state
    projection = kernel.state.followup_author_response_finalization_projection
    author_observation = kernel.state.author_observation
    final_answer_outcome = kernel.state.final_answer_outcome

    assert state["owner"] == "RunKernel.FollowupAuthorResponseFinalization"
    assert state["canonical_state"] is True
    assert state["af5a_response_candidate_consumed"] is True
    assert state["followup_author_execution_from_ad_consumed"] is False
    assert state["product_answer_ready"] is True
    assert state["final_text_included"] is True
    assert state["answer_text_output_created"] is True
    assert author_observation["final_answer_text"] == ANSWER_TEXT
    assert author_observation["product_answer_text"] == ANSWER_TEXT
    assert final_answer_outcome["final_answer_text"] == ANSWER_TEXT
    assert final_answer_outcome["product_answer_text"] == ANSWER_TEXT
    assert final_answer_outcome["final_answer_output"]["answer_text"] == ANSWER_TEXT
    assert final_answer_outcome["product_answer_ready"] is True
    assert final_answer_outcome["final_text_included"] is True
    assert final_answer_outcome["final_answer_packet_ref"] == (state["final_answer_packet_ref"])
    assert final_answer_outcome["source_refs"] == state["source_refs"]
    assert final_answer_outcome["citation_refs"] == state["citation_refs"]
    assert final_answer_outcome["caveat_refs"] == state["caveat_refs"]
    assert state["final_answer_packet_ref"]["packet_id"] == packet_before["packet_id"]
    assert state["final_answer_packet_ref"]["packet_id"] == authority_before["packet_id"]
    for surface in (state, projection, author_observation, final_answer_outcome):
        _assert_fake_model_call_custody(surface)
    assert kernel.state.followup_author_response_finalization_history == [projection]
    assert kernel.state.projections[af5b.FOLLOWUP_AUTHOR_RESPONSE_FINALIZATION_STAGE] == (projection)
    assert kernel.state.final_answer_packet == packet_before
    assert kernel.state.final_answer_authority_projection == authority_before

    for surface in (state, projection, author_observation, final_answer_outcome):
        _assert_live_model_provider_flags_false(surface)
        _assert_no_raw_prompt_request_provider_payload(surface)


def test_af5b_propagates_mocked_live_adapter_accounting_to_final_outputs() -> None:
    answer_text = "AF5B product answer exists from a bounded mocked-live adapter candidate."
    kernel = _kernel_through_af4d()
    _consume_af5a_with_text(kernel, answer_text, adapter_factory=MockLiveAF5AAdapter)

    action = kernel.authorize_followup_author_response_finalization()
    result = _execute_af5b(kernel, action=action)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_response_finalization_state
    projection = kernel.state.followup_author_response_finalization_projection
    author_observation = kernel.state.author_observation
    final_answer_outcome = kernel.state.final_answer_outcome
    for surface in (state, projection, author_observation, final_answer_outcome):
        _assert_mock_live_model_call_custody(surface)
        _assert_live_model_provider_flags_false(surface)
        _assert_no_raw_prompt_request_provider_payload(surface)
        assert surface["injected_fake_model_adapter_used"] is False
    assert author_observation["final_answer_text"] == answer_text
    assert final_answer_outcome["final_answer_output"]["answer_text"] == answer_text
    assert state["output_surface"]["product_answer_ready"] is True


def test_af5b_requires_af5a_and_rejects_old_ae() -> None:
    kernel = _kernel_through_af4d()
    with pytest.raises(RunKernelTransitionError, match="AF5A"):
        kernel.authorize_followup_author_response_finalization()

    _consume_af5a_with_text(kernel, ANSWER_TEXT)
    kernel.state.followup_author_execution_from_ad_state["owner"] = "old AE"
    with pytest.raises(RunKernelTransitionError, match="old AE"):
        kernel.authorize_followup_author_response_finalization()


def test_af5b_rejects_spoofed_observation_text_atomically() -> None:
    kernel = _kernel_through_af4d()
    _consume_af5a_with_text(kernel, ANSWER_TEXT)
    action = kernel.authorize_followup_author_response_finalization()
    result = _execute_af5b(kernel, action=action)
    spoofed = deepcopy(result.record.to_dict())
    spoofed["final_answer_outcome"]["final_answer_text"] = "spoofed answer"

    with pytest.raises(RunKernelTransitionError, match="final answer text mismatch"):
        kernel.reduce(_af5b_observation_from_state(action, spoofed))
    assert kernel.state.followup_author_response_finalization_state == {}
    assert kernel.state.author_observation == {}
    assert kernel.state.final_answer_outcome == {}


def test_af5b_static_guards_keep_live_provider_search_and_old_ae_closed() -> None:
    runtime_path = ROOT / "core" / "followup_author_response_finalization_runtime.py"
    forbidden_imports = set(
        """
        core.followup_author_execution_from_ad_runtime core.author_execution_runtime
        core.final_answer_runtime_assembly core.final_answer_runtime_adapter
        core.pipeline_orchestrator core.runtime_prompt_assembly core.llm openai
        requests httpx urllib dotenv importlib os subprocess
        """.split()
    )
    assert imported_modules(runtime_path).isdisjoint(forbidden_imports)
    runtime_source = runtime_path.read_text(encoding="utf-8")
    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(encoding="utf-8")
    af5b_sections = [
        run_kernel_source.split(
            "def authorize_followup_author_response_finalization",
            1,
        )[1].split("def authorize_followup_author_observation", 1)[0],
        run_kernel_source.split(
            "if action.action_type is ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE:\n"
            "            af5b_observed_finalization_state",
            1,
        )[1].split("self.state.reduced_action_ids.add", 1)[0],
        run_kernel_source.split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZE:",
            1,
        )[1].split(
            "elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION",
            1,
        )[0],
    ]
    for token in (
        "execute_author_action(",
        "ask_model(",
        "ActionType.AUTHOR_EXECUTE",
        "ObservationType.AUTHOR_OUTPUT_OBSERVED",
        "followup_author_execution_from_ad_runtime",
        "pipeline_orchestrator",
        "build_ordered_sources",
        "adapter_factory",
        "create_model_adapter",
        "request_live_validation_broker",
        "importlib",
    ):
        assert token not in runtime_source
        for section in af5b_sections:
            assert token not in section
    assert "python scripts/validation/run_bucket.py fast_pr" in (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert (
        "tests/test_ag96i3af5b_author_response_finalization.py::"
        "test_af5b_converts_af5a_fake_adapter_candidate_to_product_answer_text"
    ) in (ROOT / "tests" / "buckets" / "author_lane.txt").read_text(encoding="utf-8")


def _consume_af5a_with_text(
    kernel: RunKernel,
    text: str,
    *,
    adapter_factory: type[FakeAF5AAdapter] = FakeAF5AAdapter,
) -> None:
    action = kernel.authorize_followup_author_execution_from_af4d()
    result = _execute_af5a(kernel, action=action, adapter=adapter_factory(text))
    kernel.reduce(result.observation)


def _execute_af5b(kernel: RunKernel, *, action: Any) -> Any:
    return af5b.execute_followup_author_response_finalization_action(
        action,
        **_af5b_runtime_kwargs(kernel),
    )


def _af5b_runtime_kwargs(kernel: RunKernel) -> dict[str, Any]:
    state = kernel.state
    return {
        "followup_author_execution_from_af4d_state": (state.followup_author_execution_from_af4d_state),
        "followup_author_execution_from_af4d_projection": (state.followup_author_execution_from_af4d_projection),
        "followup_author_execution_from_af4d_history": (state.followup_author_execution_from_af4d_history),
        "final_answer_packet": state.final_answer_packet,
        "final_answer_authority_projection": state.final_answer_authority_projection,
    }


def _af5b_observation_from_state(action: Any, state: dict[str, Any]) -> Observation:
    return Observation.from_action(
        action,
        observation_type=ObservationType.FOLLOWUP_AUTHOR_RESPONSE_FINALIZED,
        status="completed",
        payload={"followup_author_response_finalization_state": state},
    )


def _assert_live_model_provider_flags_false(surface: dict[str, Any]) -> None:
    for flag in """
        model_execution_allowed live_provider_call_allowed real_model_called
        ask_model_called execute_author_action_called author_executor_invoked
        model_response_retained provider_payload_retained
        prompt_raw_payload_retained model_request_raw_payload_retained
        provider_raw_payload_retained payload_raw_retained
        model_response_raw_payload_retained private_logs_retained
        db_cache_rows_retained full_trace_retained live_model_call_performed
        prompt_text_retained request_text_retained
        search_executed retrieval_executed fetch_executed evidence_reselected
        citation_rendering_changed citation_formatter_invoked
    """.split():
        assert surface[flag] is False


def _assert_fake_model_call_custody(surface: dict[str, Any]) -> None:
    for field, expected in FAKE_MODEL_CALL_CUSTODY.items():
        assert surface[field] == expected


def _assert_mock_live_model_call_custody(surface: dict[str, Any]) -> None:
    for field, expected in MOCK_LIVE_MODEL_CALL_CUSTODY.items():
        assert surface[field] == expected


def _assert_no_raw_prompt_request_provider_payload(value: Any) -> None:
    forbidden_keys = """
        prompt raw_prompt prompt_text request_text raw_request_text
        model_request_text provider_payload raw_provider_payload
        model_response raw_model_response raw_text raw_response
    """.split()
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_no_raw_prompt_request_provider_payload(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_no_raw_prompt_request_provider_payload(child)
