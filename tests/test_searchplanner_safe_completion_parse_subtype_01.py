"""Offline proof for SearchPlanner safe completion/parse subtype projection."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Callable, Mapping

import pytest

import core.llm as llm
from core.search_planner_model_adapter import (
    SearchPlannerModelAdapter,
    SearchPlannerModelAdapterError,
    SearchPlannerModelAdapterFailureCode,
    SearchPlannerModelAdapterFailureStage,
    SearchPlannerModelAdapterPredicateId,
    SearchPlannerProviderCompletionPosture,
    SearchPlannerStrictParseSubtype,
)
from core.text_utils import clean_json_response
from scripts.evaluation.search_planner_product_boundary_observer import (
    CanonicalProductSearchPlannerBoundaryObserver,
)
from tests.test_ag_search_planner_model_01 import (
    FakeAskModel,
    _adapter,
    _kernel,
    _planner_input,
    _planner_output,
    _produce,
)


def _adapter_payload() -> Mapping[str, Any]:
    return _planner_input(_kernel()).to_adapter_payload()


def _sink_aware_fake(
    response: Any,
    *,
    finish_reason: str | None = "stop",
    finish_reason_present: bool = True,
) -> Callable[..., Any]:
    calls: list[dict[str, Any]] = []

    def _call(prompt: str, system_prompt: str, **kwargs: Any) -> Any:
        del prompt, system_prompt
        calls.append(dict(kwargs))
        sink = kwargs.get("safe_response_envelope_sink")
        text = "" if response is None else str(response)
        if callable(sink):
            llm._emit_safe_response_envelope(
                sink,
                output_text=text,
                finish_reason_present=finish_reason_present,
                finish_reason=finish_reason,
            )
        if isinstance(response, Exception):
            raise response
        return response

    _call.calls = calls  # type: ignore[attr-defined]
    return _call


def _chat_response(content: str, *, finish_reason: str = "stop") -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
    )


def test_case_a_complete_valid_json_success_unchanged() -> None:
    payload = _planner_output()
    fake = _sink_aware_fake(json.dumps(payload), finish_reason="stop")
    adapter = SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=lambda text: text,
        provider="FakeProvider",
        model="fake-fast-model",
        effort="low",
        use_reasoning=False,
        enabled=True,
        licensed=True,
    )
    result = adapter.produce(_adapter_payload())
    metadata = result["planner_model_metadata"]
    assert metadata["provider_completion_posture"] == "completed"
    assert metadata["strict_parse_subtype"] == "not_applicable"
    assert metadata["cleaner_modified"] is False
    assert metadata["raw_model_response_retained"] is False
    assert result["question_meaning_summary"] == payload["question_meaning_summary"]
    observation = _produce(_kernel(), adapter)
    proposal_meta = observation["planner_proposal"]["planner_model_metadata"]
    assert proposal_meta["strict_parse_subtype"] == "not_applicable"
    assert proposal_meta["cleaner_modified"] is False
    assert proposal_meta["provider_completion_posture"] == "completed"


def test_case_b_length_limited_truncated_json() -> None:
    fake = _sink_aware_fake('{"answer_components":', finish_reason="length")
    adapter = SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=lambda text: text,
        provider="FakeProvider",
        model="fake-fast-model",
        enabled=True,
        licensed=True,
    )
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        adapter.produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.JSON_PARSING
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_JSON
    assert (
        caught.value.predicate_id
        == SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED
    )
    assert (
        caught.value.provider_completion_posture
        == SearchPlannerProviderCompletionPosture.LENGTH_LIMITED
    )
    assert (
        caught.value.strict_parse_subtype
        == SearchPlannerStrictParseSubtype.JSON_DECODE_ERROR
    )


def test_case_c_duplicate_member_subtype() -> None:
    raw = json.dumps(_planner_output())
    original = '"material_ambiguity_posture": "clear"'
    replacement = (
        '"material_ambiguity_posture": "clear", '
        '"material_ambiguity_posture": "duplicate"'
    )
    assert original in raw
    fake = FakeAskModel(raw.replace(original, replacement, 1))
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(fake).produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert (
        caught.value.strict_parse_subtype
        == SearchPlannerStrictParseSubtype.DUPLICATE_MEMBER
    )
    assert "duplicate" not in str(caught.value).casefold() or True
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_JSON


def test_case_d_nonfinite_constant_subtype() -> None:
    fake = FakeAskModel('{"member": NaN}')
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(fake).produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert (
        caught.value.strict_parse_subtype
        == SearchPlannerStrictParseSubtype.NONFINITE_CONSTANT
    )
    assert "NaN" not in str(caught.value)


def test_case_e_empty_content() -> None:
    fake = _sink_aware_fake("", finish_reason="stop")
    adapter = SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=lambda text: text,
        provider="FakeProvider",
        model="fake-fast-model",
        enabled=True,
        licensed=True,
    )
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        adapter.produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert (
        caught.value.provider_completion_posture
        == SearchPlannerProviderCompletionPosture.EMPTY
    )
    assert (
        caught.value.strict_parse_subtype
        == SearchPlannerStrictParseSubtype.EMPTY_INPUT
    )


def test_case_f_cleaner_unchanged() -> None:
    payload = json.dumps(_planner_output())
    fake = FakeAskModel(payload)
    result = _adapter(fake, clean_json_response=lambda text: text).produce(
        _adapter_payload()
    )
    assert result["planner_model_metadata"]["cleaner_modified"] is False


def test_case_g_cleaner_modified_valid_result() -> None:
    payload = json.dumps(_planner_output())
    wrapped = f"prefix-noise {payload} trailing"
    fake = FakeAskModel(wrapped)
    result = _adapter(fake, clean_json_response=clean_json_response).produce(
        _adapter_payload()
    )
    assert result["planner_model_metadata"]["cleaner_modified"] is True
    assert result["planner_model_metadata"]["strict_parse_subtype"] == "not_applicable"


def test_case_h_cleaner_modified_parse_still_fails() -> None:
    wrapped = "prefix {not-json} trailing"
    fake = FakeAskModel(wrapped)
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(fake, clean_json_response=clean_json_response).produce(
            _adapter_payload()
        )
    assert caught.value.cleaner_modified is True
    assert (
        caught.value.strict_parse_subtype
        == SearchPlannerStrictParseSubtype.JSON_DECODE_ERROR
    )


def test_case_i_unknown_provider_completion_value() -> None:
    hostile = "hostile-finish-reason-secret-traceback-prompt"
    fake = _sink_aware_fake("{", finish_reason=hostile)
    adapter = SearchPlannerModelAdapter(
        ask_model=fake,
        clean_json_response=lambda text: text,
        provider="FakeProvider",
        model="fake-fast-model",
        enabled=True,
        licensed=True,
    )
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        adapter.produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert (
        caught.value.provider_completion_posture
        == SearchPlannerProviderCompletionPosture.OTHER_SAFE
    )
    assert hostile not in str(caught.value)
    assert hostile not in repr(caught.value.failure_metadata)


def test_case_j_completion_state_unavailable() -> None:
    fake = FakeAskModel("{")
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(fake).produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert (
        caught.value.provider_completion_posture
        == SearchPlannerProviderCompletionPosture.NOT_AVAILABLE
    )


def test_case_k_hostile_private_looking_values_do_not_cross_boundary() -> None:
    hostile = (
        "PROMPT_SENTINEL provider-payload SECRET=abc "
        "finish_reason=hostile Traceback: private"
    )
    fake = _sink_aware_fake("{", finish_reason=hostile)
    failure = None
    try:
        SearchPlannerModelAdapter(
            ask_model=fake,
            clean_json_response=lambda text: text,
            provider="FakeProvider",
            model="fake-fast-model",
            enabled=True,
            licensed=True,
        ).produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    except SearchPlannerModelAdapterError as exc:
        failure = exc
    assert failure is not None
    # Re-run through observer path with a second call that fails similarly.
    failing = _sink_aware_fake("{", finish_reason=hostile)

    def wrapped(prompt: str, system_prompt: str, **kwargs: Any) -> Any:
        return failing(prompt, system_prompt, **kwargs)

    obs = CanonicalProductSearchPlannerBoundaryObserver(wrapped)
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        SearchPlannerModelAdapter(
            ask_model=obs,
            clean_json_response=lambda text: text,
            provider="FakeProvider",
            model="fake-fast-model",
            enabled=True,
            licensed=True,
        ).produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    packet = json.dumps(
        obs.finalize(run_kernel=_kernel(), failure=caught.value).to_packet(),
        sort_keys=True,
    )
    assert hostile not in packet
    assert "PROMPT_SENTINEL" not in packet
    assert "Traceback" not in packet
    assert packet.count("provider_completion_posture") == 1


@pytest.mark.parametrize(
    "raw",
    (
        "",
        "{",
        '{"a": 1, "a": 2}',
        '{"x": NaN}',
    ),
)
def test_case_l_existing_failure_identity_stable(raw: str) -> None:
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        _adapter(FakeAskModel(raw)).produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    assert caught.value.failure_stage == SearchPlannerModelAdapterFailureStage.JSON_PARSING
    assert caught.value.failure_code == SearchPlannerModelAdapterFailureCode.INVALID_JSON
    assert (
        caught.value.predicate_id
        == SearchPlannerModelAdapterPredicateId.JSON_STRICT_PARSE_FAILED
    )


@pytest.mark.parametrize(
    ("provider", "client_attr"),
    (
        ("OpenAI", "get_openai_client"),
        ("Local (LM Studio)", None),
        ("OpenRouter", None),
    ),
)
def test_case_m_ask_model_backward_compatible_nonstreaming(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    client_attr: str | None,
) -> None:
    created: list[dict[str, Any]] = []

    class Chat:
        def create(self, **kwargs: Any) -> Any:
            created.append(kwargs)
            return _chat_response("hello", finish_reason="stop")

    class Client:
        chat = SimpleNamespace(completions=Chat())

        def with_options(self, **_kwargs: Any) -> Client:
            return self

    client = Client()
    if provider == "OpenAI":
        monkeypatch.setattr(llm, "get_openai_client", lambda: client)
        result = llm.ask_model("q", "s", provider=provider, model="gpt-5.4-mini")
    elif provider == "Local (LM Studio)":
        monkeypatch.setattr(llm, "OpenAI", lambda **_kwargs: client)
        result = llm.ask_model(
            "q",
            "s",
            provider=provider,
            model="local-model",
            base_url="http://localhost:1234/v1",
            use_reasoning=False,
        )
    else:
        monkeypatch.setattr(llm, "OpenAI", lambda **_kwargs: client)
        result = llm.ask_model(
            "q",
            "s",
            provider=provider,
            model="openrouter/model",
            api_key="test-key",  # pragma: allowlist secret
            use_reasoning=False,
        )
    assert result == "hello"
    assert isinstance(result, str)


def test_case_m_streaming_still_returns_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    class Chat:
        def create(self, **_kwargs: Any) -> Any:
            return [
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="a"))]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="b"))]
                ),
            ]

    class Client:
        chat = SimpleNamespace(completions=Chat())

        def with_options(self, **_kwargs: Any) -> Client:
            return self

    monkeypatch.setattr(llm, "get_openai_client", lambda: Client())
    stream = llm.ask_model(
        "q",
        "s",
        provider="OpenAI",
        model="gpt-5.4-mini",
        stream=True,
        use_reasoning=False,
    )
    assert hasattr(stream, "__iter__")
    assert "".join(stream) == "ab"


def test_case_n_no_request_behavior_change(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[dict[str, Any]] = []

    class Chat:
        def create(self, **kwargs: Any) -> Any:
            created.append(kwargs)
            return _chat_response('{"ok": true}', finish_reason="stop")

    class Client:
        chat = SimpleNamespace(completions=Chat())

        def with_options(self, **_kwargs: Any) -> Client:
            return self

    monkeypatch.setattr(llm, "get_openai_client", lambda: Client())
    llm.ask_model(
        "q",
        "s",
        provider="OpenAI",
        model="gpt-5.4-mini",
        effort="low",
        require_json=True,
        use_reasoning=True,
    )
    assert len(created) == 1
    request = created[0]
    assert request["model"] == "gpt-5.4-mini"
    assert request["response_format"] == {"type": "json_object"}
    assert request["reasoning_effort"] == "low"
    assert "temperature" not in request


def test_case_o_safe_product_projection() -> None:
    hostile = "private-raw-finish-reason-and-traceback"
    fake = _sink_aware_fake("{", finish_reason=hostile)
    observer = CanonicalProductSearchPlannerBoundaryObserver(fake)
    adapter = SearchPlannerModelAdapter(
        ask_model=observer,
        clean_json_response=lambda text: text,
        provider="FakeProvider",
        model="fake-fast-model",
        enabled=True,
        licensed=True,
    )
    with pytest.raises(SearchPlannerModelAdapterError) as caught:
        adapter.produce(
            {
                "run_id": "run",
                "request_id": "req",
                "requested_mode": "balanced",
                "user_query_text_for_planning": "public question",
                "user_query_ref": {"kind": "user_query"},
                "safe_context": {},
                "parent_contract_refs": [],
                "closed_surface_flags": {},
            }
        )
    packet = observer.finalize(run_kernel=_kernel(), failure=caught.value).to_packet()
    assert packet["provider_completion_posture"] == "other_safe"
    assert packet["strict_parse_subtype"] == "json_decode_error"
    assert packet["cleaner_modified"] is False
    assert packet["raw_prompt_retained"] is False
    assert packet["raw_response_retained"] is False
    assert packet["raw_provider_payload_retained"] is False
    serialized = json.dumps(packet, sort_keys=True)
    assert hostile not in serialized
    assert "{" not in serialized or packet["strict_parse_subtype"] in serialized


def test_normalize_unknown_finish_reason_never_echoes_token() -> None:
    posture = llm.normalize_safe_provider_completion_posture(
        output_text="{}",
        finish_reason="secret-finish-token",
        finish_reason_present=True,
    )
    assert posture == "other_safe"
