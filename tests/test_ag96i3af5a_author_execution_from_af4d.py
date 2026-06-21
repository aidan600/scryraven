from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

import core.followup_author_execution_from_af4d_runtime as af5a
from core.run_kernel import ActionType, ObservationType, RunKernel, RunKernelTransitionError
from tests.ag96_static_guards import imported_modules
from tests.test_ag96i3ae_author_execution_from_ad import (
    _kernel_through_ad,
    _stale_ad_action_and_observation,
)
from tests.test_ag96i3af4_author_invocation_construction import (
    _af4_observation,
    _consume_bridge,
)
from tests.test_ag96i3af4_author_invocation_construction import (
    _candidate as _af4_candidate,
)
from tests.test_ag96i3af4b2_author_evidence_content_bridge import (
    _bridge_observation as _af4b2_observation,
)
from tests.test_ag96i3af4b2_author_evidence_content_bridge import (
    _candidate as _af4b2_candidate,
)
from tests.test_ag96i3af4d_author_model_request_assembly import (
    REQUEST,
    _af4d_observation,
    _kernel_through_af4c,
)
from tests.test_ag96i3q1_citation_eligibility import (
    _inject_external_stale_action_and_observation,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_RESPONSE_TAIL = "RAW_MODEL_RESPONSE_TAIL_DO_NOT_RETAIN"
SAFE_CANDIDATE_PREFIX = "Bounded sanitized AF5A author response candidate."
FORBIDDEN_KEYS = "prompt_text raw_prompt request_text raw_request_text model_request_text sanitized_excerpt_text model_response raw_model_response final_answer_text report_text product_output provider_payload raw_provider_payload output author_observation final_answer_outcome".split()
FORBIDDEN_TEXT = [
    REQUEST,
    "Bounded sanitized answer-bearing excerpt",
    "FINAL ANSWER PACKET AUTHORITY",
    RAW_RESPONSE_TAIL,
    "product output",
]
FALSE_FLAGS = "model_execution_allowed live_provider_call_allowed real_model_called ask_model_called execute_author_action_called author_observation_created final_answer_outcome_created prompt_text_retained request_text_retained model_response_retained provider_payload_retained report_text_retained final_text_retained final_text_included product_answer_ready citation_strings_included ordered_product_source_output_created".split()
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


class FakeAF5AAdapter:
    def __init__(self, response_text: str | None = None) -> None:
        self.response_text = response_text or (
            SAFE_CANDIDATE_PREFIX + " " + ("x" * af5a.MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS) + RAW_RESPONSE_TAIL
        )
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        request_text: str,
        *,
        request_digest: str,
        request_length: int,
        request_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "request_text": request_text,
                "request_digest": request_digest,
                "request_length": request_length,
                "request_metadata": deepcopy(request_metadata),
            }
        )
        return {
            "candidate_text": self.response_text,
            "metadata": {
                "adapter_kind": "injected_fake_model_adapter",
                "adapter_invocation_count": len(self.calls),
                "fake_adapter_used": True,
                "request_digest_seen": request_digest,
                "request_length_seen": len(request_text),
            },
        }


class MockLiveAF5AAdapter(FakeAF5AAdapter):
    def __call__(
        self,
        request_text: str,
        *,
        request_digest: str,
        request_length: int,
        request_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        response = super().__call__(
            request_text,
            request_digest=request_digest,
            request_length=request_length,
            request_metadata=request_metadata,
        )
        response["metadata"].update(
            {
                "adapter_kind": "mock_live_model_adapter",
                "author_model_call_mode": "live_adapter_mocked",
                "live_adapter_mocked": True,
            }
        )
        return response


def test_af5a_happy_path_calls_fake_adapter_once_and_retains_bounded_candidate() -> None:
    kernel = _kernel_through_af4d()
    before = _closed_snapshot(kernel)
    af4d_before = before["af4d_state"]
    action = kernel.authorize_followup_author_execution_from_af4d()
    assert action.stage == af5a.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE
    assert action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D
    assert action.expected_observation_type is (ObservationType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_OBSERVED)
    assert action.inputs["status"] == af5a.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS
    assert action.inputs["af4d_author_model_request_assembly_id"] == (af4d_before["author_model_request_assembly_id"])
    assert action.inputs["af4d_author_model_request_digest"] == af4d_before["author_model_request_digest"]

    fake = FakeAF5AAdapter()
    result = _execute_af5a(kernel, action=action, adapter=fake)
    assert len(fake.calls) == 1
    assert REQUEST in fake.calls[0]["request_text"]
    assert "Bounded sanitized answer-bearing excerpt" in fake.calls[0]["request_text"]
    assert fake.calls[0]["request_digest"] == af4d_before["author_model_request_digest"]

    kernel.reduce(result.observation)

    state = kernel.state.followup_author_execution_from_af4d_state
    projection = kernel.state.followup_author_execution_from_af4d_projection
    candidate = state["bounded_sanitized_author_response_candidate"]
    receipt = state["adapter_receipt_metadata"]
    for surface in (state, projection):
        assert surface["owner"] == "RunKernel.FollowupAuthorExecutionFromAF4D"
        assert surface["canonical_state"] is True
        assert surface["status"] == af5a.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STATUS
        assert (
            surface["author_execution_from_af4d_mode"] == af5a.AG96I3AF5A_AF4D_BOUND_AUTHOR_EXECUTION_LIVE_DISABLED_MODE
        )
        assert surface["af4d_author_model_request_digest"] == af4d_before["author_model_request_digest"]
        assert surface["reconstructed_author_model_request_digest"] == af4d_before["author_model_request_digest"]
        assert surface["af4d_reconstructed_request_digest_match"] is True
        _assert_closed(surface)
        _assert_fake_model_call_custody(surface)
        _assert_absent(surface, FORBIDDEN_KEYS, FORBIDDEN_TEXT)
    for flag in "af4d_author_model_request_consumed af4c_author_invocation_consumed af4b2_author_evidence_content_consumed".split():
        assert state[flag] is True
    assert state["transient_author_model_request_text_retained"] is False
    assert candidate["bounded_sanitized_author_response_candidate_text"].startswith(SAFE_CANDIDATE_PREFIX)
    assert candidate["author_response_candidate_length"] == (af5a.MAX_BOUNDED_AUTHOR_RESPONSE_CANDIDATE_CHARS)
    assert candidate["author_response_candidate_digest"] == (state["author_response_candidate_digest"])
    assert receipt["adapter_invocation_count"] == 1
    assert receipt["fake_adapter_used"] is True
    assert receipt["request_digest_seen"] == af4d_before["author_model_request_digest"]
    assert receipt["request_text_retained"] is False
    assert receipt["model_response_retained"] is False
    assert receipt["real_model_called"] is False
    assert receipt["ask_model_called"] is False
    _assert_fake_model_call_custody(receipt)
    assert kernel.state.followup_author_execution_from_af4d_history == [projection]
    assert kernel.state.projections[af5a.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D_STAGE] == (projection)
    assert _closed_snapshot(kernel) == before


def test_af5a_mocked_live_adapter_records_mock_only_accounting_without_live_flags() -> None:
    kernel = _kernel_through_af4d()
    action = kernel.authorize_followup_author_execution_from_af4d()
    adapter = MockLiveAF5AAdapter("Bounded sanitized mocked-live AF5A author response candidate.")

    result = _execute_af5a(kernel, action=action, adapter=adapter)
    kernel.reduce(result.observation)

    state = kernel.state.followup_author_execution_from_af4d_state
    projection = kernel.state.followup_author_execution_from_af4d_projection
    receipt = state["adapter_receipt_metadata"]
    candidate = state["bounded_sanitized_author_response_candidate"]
    assert len(adapter.calls) == 1
    assert candidate["bounded_sanitized_author_response_candidate_text"] == (
        "Bounded sanitized mocked-live AF5A author response candidate."
    )
    for surface in (state, projection, receipt):
        _assert_mock_live_model_call_custody(surface)
        assert surface["live_model_call_performed"] is False
        assert surface["model_calls_used"] == 0
        assert surface["mock_model_adapter_calls_used"] == 1
        assert surface["fake_adapter_used"] is False
        assert surface["live_adapter_mocked"] is True
        assert surface["prompt_raw_payload_retained"] is False
        assert surface["model_request_raw_payload_retained"] is False
        assert surface["provider_raw_payload_retained"] is False
        assert surface["payload_raw_retained"] is False
        assert surface["model_response_raw_payload_retained"] is False
    assert state["injected_fake_model_adapter_used"] is False
    assert projection["injected_fake_model_adapter_used"] is False
    assert receipt["adapter_kind"] == "mock_live_model_adapter"
    _assert_absent(state, FORBIDDEN_KEYS, FORBIDDEN_TEXT)


def test_af5a_requires_af4d_even_if_ad_af4c_exist() -> None:
    kernel = _kernel_through_af4c()
    assert kernel.state.followup_author_invocation_construction_state
    assert kernel.state.followup_author_evidence_content_bridge_state
    with pytest.raises(RunKernelTransitionError, match="requires canonical AF4D"):
        kernel.authorize_followup_author_execution_from_af4d()


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda k: k.state.followup_author_model_request_assembly_projection.update({"canonical_state": False}),
            "canonical AF4D",
        ),
        (
            lambda k: k.state.followup_author_invocation_construction_state.update(
                {"ag96i3_author_invocation_digest": "stale"}
            ),
            "AF4D/AF4C digest",
        ),
        (
            lambda k: k.state.followup_author_evidence_content_bridge_state[
                "sanitized_author_evidence_content_payload"
            ][0].update({"sanitized_excerpt_text": "stale"}),
            "AF4B2 content payload digest",
        ),
    ],
)
def test_af5a_rejects_stale_af4d_af4c_or_af4b2(
    mutate: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_af4d()
    action = kernel.authorize_followup_author_execution_from_af4d()
    result = _execute_af5a(kernel, action=action)
    mutate(kernel)
    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.reduce(result.observation)
    assert kernel.state.followup_author_execution_from_af4d_state == {}


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda k: k.state.followup_author_execution_from_ad_state.update({"created": True}),
            "old AE",
        ),
        (lambda k: k.state.author_observation.update({"created": True}), "Author/final"),
        (lambda k: k.state.final_answer_outcome.update({"created": True}), "Author/final"),
    ],
)
def test_af5a_rejects_old_ae_or_preexisting_author_final_outcome(
    mutate: Callable[[RunKernel], None],
    match: str,
) -> None:
    kernel = _kernel_through_af4d()
    mutate(kernel)
    with pytest.raises(RunKernelTransitionError, match=match):
        kernel.authorize_followup_author_execution_from_af4d()


def test_af5a_duplicate_reduction_rejected() -> None:
    kernel = _kernel_through_af4d()
    first = kernel.authorize_followup_author_execution_from_af4d()
    first_result = _execute_af5a(kernel, action=first, adapter=FakeAF5AAdapter())
    duplicate = kernel.authorize_followup_author_execution_from_af4d()
    duplicate_result = _execute_af5a(
        kernel,
        action=duplicate,
        adapter=FakeAF5AAdapter(response_text="Another bounded sanitized candidate."),
    )

    kernel.reduce(first_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already completed"):
        kernel.authorize_followup_author_execution_from_af4d()
    with pytest.raises(RunKernelTransitionError, match="duplicate AG-96I3AF5A"):
        kernel.reduce(duplicate_result.observation)
    with pytest.raises(RunKernelTransitionError, match="already reduced"):
        kernel.reduce(first_result.observation)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _stale_ad_action_and_observation(),
        lambda: _stale_af4b2_action_and_observation(),
        lambda: _stale_af4c_action_and_observation(),
        lambda: _stale_af4d_action_and_observation(),
    ],
)
def test_af5a_rejects_stale_upstream_reductions_after_success(
    factory: Callable[[], tuple[RunKernel, Any, Any]],
) -> None:
    source_kernel, stale_action, stale_observation = factory()
    kernel = _kernel_through_af4d()
    _consume_af5a(kernel)
    _, injected = _inject_external_stale_action_and_observation(
        kernel,
        source_kernel,
        stale_action,
        stale_observation,
    )
    with pytest.raises(RunKernelTransitionError, match="AG-96I3AF5A|stale"):
        kernel.reduce(injected)


def test_af5a_static_guards_and_fast_custody_lane() -> None:
    runtime_path = ROOT / "core" / "followup_author_execution_from_af4d_runtime.py"
    forbidden_imports = set(
        "core.author_execution_runtime core.followup_author_execution_from_ad_runtime core.runtime_prompt_assembly core.final_answer_runtime_assembly core.final_answer_runtime_adapter core.post_author_output_projection core.pipeline_orchestrator core.llm openai requests httpx urllib dotenv importlib os subprocess".split()
    )
    assert imported_modules(runtime_path).isdisjoint(forbidden_imports)
    runtime_source = runtime_path.read_text(encoding="utf-8")
    run_kernel_source = (ROOT / "core" / "run_kernel.py").read_text(encoding="utf-8")
    af5a_sections = [
        run_kernel_source.split("def authorize_followup_author_execution_from_af4d", 1)[1].split(
            "def authorize_followup_author_observation", 1
        )[0],
        run_kernel_source.split('observation.payload.get("followup_author_execution_from_af4d_state")', 1)[1].split(
            "self.state.reduced_action_ids.add", 1
        )[0],
        run_kernel_source.split("elif action.action_type is ActionType.FOLLOWUP_AUTHOR_EXECUTION_FROM_AF4D:", 1)[
            1
        ].split("elif action.action_type is ActionType.FOLLOWUP_AUTHOR_OBSERVATION", 1)[0],
    ]
    for token in "ask_model( execute_author_action( ActionType.AUTHOR_EXECUTE ObservationType.AUTHOR_OUTPUT_OBSERVED build_followup_author_execution_from_ad_record execute_followup_author_execution_from_ad_action author_execution_runtime core.llm pipeline_orchestrator final_answer_runtime build_ordered_sources adapter_factory create_model_adapter request_live_validation_broker importlib search_web retrieve( retrieval_executed=True fetch( render_citation format_citation".split():
        assert token not in runtime_source
        for section in af5a_sections:
            assert token not in section
    assert "python scripts/validation/run_bucket.py fast_pr" in (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert (
        "tests/test_ag96i3af5a_author_execution_from_af4d.py::"
        "test_af5a_happy_path_calls_fake_adapter_once_and_retains_bounded_candidate"
    ) in (ROOT / "tests" / "buckets" / "author_lane.txt").read_text(encoding="utf-8")


def _kernel_through_af4d() -> RunKernel:
    kernel = _kernel_through_af4c()
    action = kernel.authorize_followup_author_model_request_assembly()
    kernel.reduce(_af4d_observation(kernel, action))
    return kernel


def _execute_af5a(kernel: RunKernel, *, action: Any, adapter: FakeAF5AAdapter | None = None) -> Any:
    return af5a.execute_followup_author_execution_from_af4d_action(
        action,
        model_adapter=adapter or FakeAF5AAdapter(),
        **_af5a_runtime_kwargs(kernel),
    )


def _consume_af5a(kernel: RunKernel) -> tuple[Any, Any]:
    action = kernel.authorize_followup_author_execution_from_af4d()
    result = _execute_af5a(kernel, action=action)
    kernel.reduce(result.observation)
    return action, result


def _af5a_runtime_kwargs(kernel: RunKernel) -> dict[str, Any]:
    state = kernel.state
    prefixes = "followup_author_evidence_content_bridge followup_author_invocation_construction followup_author_model_request_assembly".split()
    kwargs = {
        f"{prefix}_{suffix}": getattr(state, f"{prefix}_{suffix}")
        for prefix in prefixes
        for suffix in ("state", "projection", "history")
    }
    kwargs["run_request"] = state.request
    return kwargs


def _closed_snapshot(kernel: RunKernel) -> dict[str, Any]:
    state = kernel.state
    names = "final_answer_packet final_answer_authority_projection author_observation final_answer_outcome followup_author_execution_from_ad_state followup_author_observation_state followup_author_model_request_assembly_state followup_author_model_request_assembly_projection followup_author_model_request_assembly_history".split()
    snapshot = {name: deepcopy(getattr(state, name)) for name in names}
    snapshot["af4d_state"] = snapshot["followup_author_model_request_assembly_state"]
    return snapshot


def _stale_af4b2_action_and_observation() -> tuple[RunKernel, Any, Any]:
    source = _kernel_through_ad()
    action = source.authorize_followup_author_evidence_content_bridge(
        inputs={"sanitized_author_evidence_excerpt_candidates": [_af4b2_candidate(source)]}
    )
    return source, action, _af4b2_observation(source, action)


def _stale_af4c_action_and_observation() -> tuple[RunKernel, Any, Any]:
    source = _kernel_through_ad()
    _consume_bridge(source, _af4_candidate(source, text="Another stale excerpt."))
    action = source.authorize_followup_author_invocation_construction()
    return source, action, _af4_observation(source, action)


def _stale_af4d_action_and_observation() -> tuple[RunKernel, Any, Any]:
    source = _kernel_through_af4c()
    action = source.authorize_followup_author_model_request_assembly()
    return source, action, _af4d_observation(source, action)


def _assert_closed(surface: dict[str, Any]) -> None:
    for flag in FALSE_FLAGS:
        assert surface[flag] is False
    assert surface["author_execution_deferred"] is True
    assert surface["live_validation_not_run"] is True
    assert surface["not_for_product_answer_activation"] is True
    assert surface["injected_fake_model_adapter_used"] is True


def _assert_fake_model_call_custody(surface: dict[str, Any]) -> None:
    for field, expected in FAKE_MODEL_CALL_CUSTODY.items():
        assert surface[field] == expected


def _assert_mock_live_model_call_custody(surface: dict[str, Any]) -> None:
    for field, expected in MOCK_LIVE_MODEL_CALL_CUSTODY.items():
        assert surface[field] == expected


def _assert_absent(
    value: Any,
    forbidden_keys: list[str],
    forbidden_text: list[str],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in forbidden_keys
            _assert_absent(child, forbidden_keys, forbidden_text)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            _assert_absent(child, forbidden_keys, forbidden_text)
    elif isinstance(value, str):
        for marker in forbidden_text:
            assert marker not in value
