"""Mechanical Responses API checks, independent of specific models or prompts."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
import requests

from scryraven.model import ModelConfig, ModelError, ModelRole, OpenAIModel


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_model_config_has_research_and_answer_fast_defaults():
    assert ModelConfig() == ModelConfig(
        research=ModelRole("gpt-6-luna", "high", "fast"),
        answer=ModelRole("gpt-6-sol", "medium", "fast"),
    )


@pytest.mark.parametrize("phase", [None, "final_answer"])
def test_roles_structured_request_and_final_message_only(monkeypatch, phase):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response({"status": "completed", "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "phase": "commentary", "content": [{"type": "output_text", "text": "An intermediate update"}]},
            {"type": "message", "content": [{"type": "output_text", "text": '{"intermediate":"update"}'}]},
            {"type": "message", "phase": phase, "content": [{"type": "output_text", "text": '{"answer":"ok"}'}]},
        ]})

    config = ModelConfig(ModelRole("small-configured-model", ""), ModelRole("strong-configured-model", "medium"))
    model = OpenAIModel(config, post=post)
    schema = {"type": "object", "additionalProperties": False, "properties": {}, "required": []}
    for stage in ("research", "answer"):
        assert model(stage, "instructions", {"question": "test"}, schema) == '{"answer":"ok"}'
    assert [call[1]["json"]["model"] for call in calls] == [config.research.model, config.answer.model]
    for url, kwargs in calls:
        assert url == "https://api.openai.com/v1/responses"
        payload = kwargs["json"]
        assert json.loads("".join(block["text"] for block in payload["input"][1]["content"])) == {"question": "test"}
        assert payload["text"]["format"]["schema"] == schema
        assert payload["text"]["format"]["strict"] is True
        assert payload["store"] is False
        assert "tools" not in payload
        if payload["model"] == config.research.model:
            assert "reasoning" not in payload
        else:
            assert payload["reasoning"] == {"effort": config.answer.reasoning}


def test_default_transport_uses_recommended_stages_not_obsolete_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    monkeypatch.setenv("SCRYRAVEN_FAST_MODEL", "configured-research")
    monkeypatch.setenv("SCRYRAVEN_FAST_REASONING", "low")
    monkeypatch.setenv("SCRYRAVEN_SMART_MODEL", "configured-answer")
    monkeypatch.setenv("SCRYRAVEN_SMART_REASONING", "high")
    calls = []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return Response({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{}"}]},
        ]})

    model = OpenAIModel(post=post)
    model("research", "prompt", {}, {})
    model("answer", "prompt", {}, {})
    assert [(call["model"], call["reasoning"]["effort"], call["service_tier"])
            for call in calls] == [
        ("gpt-6-luna", "high", "fast"), ("gpt-6-sol", "medium", "fast"),
    ]


def test_service_tier_is_selected_per_semantic_stage_and_returned_tier_is_observed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []
    usage = []

    def post(_url, **kwargs):
        payload = kwargs["json"]
        calls.append(payload)
        return Response({
            "status": "completed",
            "service_tier": "priority" if payload["service_tier"] == "fast" else "default",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}],
        })

    model = OpenAIModel(ModelConfig(
        ModelRole("gpt-6-luna", "medium", "fast"),
        ModelRole("gpt-6-sol", "medium", "default"),
    ), post=post, usage_observer=usage.append)
    model("research", "prompt", {}, {})
    model("answer", "prompt", {}, {})
    assert [(call["model"], call["reasoning"]["effort"], call["service_tier"])
            for call in calls] == [
                ("gpt-6-luna", "medium", "fast"),
                ("gpt-6-sol", "medium", "default"),
            ]
    assert [(item.requested_service_tier, item.returned_service_tier) for item in usage] == [
        ("fast", "priority"), ("default", "default"),
    ]


def test_explicit_none_service_tier_omits_request_field(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return Response({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{}"}]},
        ]})

    config = ModelConfig(research=ModelRole("gpt-6-luna", "high", None))
    OpenAIModel(config, post=post)("research", "prompt", {}, {})
    assert "service_tier" not in calls[0]


@pytest.mark.parametrize("data,code", [
    ({"status": "incomplete", "output": []}, "model_response_incomplete"),
    ({"status": "incomplete", "incomplete_details": {"reason": "content_filter"}},
     "model_response_incomplete_content_filter"),
    ({"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}},
     "model_response_incomplete_max_output_tokens"),
    ({"status": "incomplete", "incomplete_details": {"reason": "private-provider-detail"}},
     "model_response_incomplete"),
    ({"status": "incomplete", "incomplete_details": {"reason": ["private-provider-detail"]}},
     "model_response_incomplete"),
    ({"status": "incomplete", "incomplete_details": "private-provider-detail"},
     "model_response_incomplete"),
    ({"status": "completed", "output": []}, "model_response_empty"),
    ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "private details"}]}]}, "model_refused"),
    ({"status": "completed", "output": None}, "malformed_model_response"),
])
def test_provider_failures_do_not_expose_raw_payloads(monkeypatch, data, code):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    model = OpenAIModel(post=lambda *a, **k: Response(data))
    with pytest.raises(ModelError, match=f"^{code}$"):
        model("answer", "private prompt", {}, {})


def test_connection_failure_does_not_expose_request_details(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")

    def failed(*args, **kwargs):
        raise requests.ConnectionError("secret-bearing request detail")

    with pytest.raises(ModelError, match="^model_transport_failed$"):
        OpenAIModel(post=failed)("research", "prompt", {}, {})


def test_timeout_has_a_safe_distinct_transport_code(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")

    def timed_out(*args, **kwargs):
        raise requests.Timeout("secret-bearing request detail")

    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        OpenAIModel(post=timed_out)("answer", "prompt", {}, {})


def test_http_failure_keeps_its_safe_transport_code(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")

    def rejected(*args, **kwargs):
        response = requests.Response()
        response.status_code = 429
        raise requests.HTTPError("private-provider-detail", response=response)

    with pytest.raises(ModelError, match="^model_rate_limited$"):
        OpenAIModel(post=rejected)("answer", "prompt", {}, {})


def test_answer_calculator_continues_statelessly_and_preserves_chained_results(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls, calculations, usage = [], [], []
    replies = [
        {"status": "completed", "usage": {"input_tokens": 11}, "output": [
            {"type": "reasoning", "id": "rs_1", "encrypted_content": "opaque-1"},
            {"type": "function_call", "id": "fc_1", "call_id": "call_1",
             "name": "calculate", "arguments": '{"expression":"2 + 3"}'},
        ]},
        {"status": "completed", "usage": {"input_tokens": 17}, "output": [
            {"type": "reasoning", "id": "rs_2", "encrypted_content": "opaque-2"},
            {"type": "function_call", "id": "fc_2", "call_id": "call_2",
             "name": "calculate", "arguments": '{"expression":"5 * 4"}'},
        ]},
        {"status": "completed", "usage": {"input_tokens": 23}, "output": [
            {"type": "message", "phase": "final_answer", "content": [
                {"type": "output_text", "text": '{"answer":"20"}'},
            ]},
        ]},
    ]

    def post(_url, **kwargs):
        calls.append(deepcopy(kwargs["json"]))
        return Response(replies.pop(0))

    def calculate(expression):
        return {"ok": True, "value": {"2 + 3": "5", "5 * 4": "20"}[expression]}

    result = OpenAIModel(post=post, usage_observer=usage.append)(
        "answer", "prompt", {"question": "private question"}, {},
        calculator=calculate,
        on_calculation=lambda sequence, expression, output: calculations.append(
            (sequence, expression, output)),
    )
    assert result == '{"answer":"20"}'
    assert not replies and len(calls) == 3
    assert calculations == [
        (1, "2 + 3", {"ok": True, "value": "5"}),
        (2, "5 * 4", {"ok": True, "value": "20"}),
    ]
    assert len(usage) == 3 and [item.input_tokens for item in usage] == [11, 17, 23]
    assert all(call["store"] is False and "previous_response_id" not in call for call in calls)
    assert all(call["tools"][0]["name"] == "calculate" for call in calls)
    assert all(call["include"] == ["reasoning.encrypted_content"] for call in calls)
    assert calls[1]["input"][-3:] == [
        {"type": "reasoning", "id": "rs_1", "encrypted_content": "opaque-1"},
        {"type": "function_call", "id": "fc_1", "call_id": "call_1",
         "name": "calculate", "arguments": '{"expression":"2 + 3"}'},
        {"type": "function_call_output", "call_id": "call_1",
         "output": '{"ok": true, "value": "5"}'},
    ]
    assert calls[2]["input"][-3:] == [
        {"type": "reasoning", "id": "rs_2", "encrypted_content": "opaque-2"},
        {"type": "function_call", "id": "fc_2", "call_id": "call_2",
         "name": "calculate", "arguments": '{"expression":"5 * 4"}'},
        {"type": "function_call_output", "call_id": "call_2",
         "output": '{"ok": true, "value": "20"}'},
    ]


def test_invalid_tool_arguments_return_bounded_error_to_same_answer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls, observed = [], []
    replies = [
        {"status": "completed", "output": [
            {"type": "function_call", "call_id": "bad", "name": "calculate",
             "arguments": "not-json"},
        ]},
        {"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{}"}]},
        ]},
    ]

    def post(_url, **kwargs):
        calls.append(deepcopy(kwargs["json"]))
        return Response(replies.pop(0))

    assert OpenAIModel(post=post)(
        "answer", "prompt", {}, {},
        calculator=lambda expression: (_ for _ in ()).throw(AssertionError(expression)),
        on_calculation=lambda *item: observed.append(item),
    ) == "{}"
    assert calls[1]["input"][-1] == {
        "type": "function_call_output", "call_id": "bad",
        "output": '{"error": "invalid_tool_arguments"}',
    }
    assert observed == [(1, "not-json", {"error": "invalid_tool_arguments"})]


def test_answer_continuation_obeys_remaining_time_before_next_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []
    seconds = [4.0]

    def post(_url, **kwargs):
        calls.append(kwargs["timeout"])
        seconds[0] = 0.0
        return Response({"status": "completed", "output": [
            {"type": "function_call", "call_id": "first", "name": "calculate",
             "arguments": '{"expression":"1 + 1"}'},
        ]})

    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        OpenAIModel(post=post)("answer", "prompt", {}, {},
                               calculator=lambda _: {"ok": True, "value": "2"},
                               remaining_seconds=lambda: seconds[0])
    assert len(calls) == 1 and 0 < calls[0] <= 4.0


def test_runtime_deadline_keeps_configured_timeout_per_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    now = [0.0]
    monkeypatch.setattr("scryraven.model.monotonic", lambda: now[0])
    timeouts = []

    def post(_url, **kwargs):
        timeouts.append(kwargs["timeout"])
        if len(timeouts) == 1:
            now[0] = 18.0
            return Response({"status": "completed", "output": [
                {"type": "function_call", "call_id": "first", "name": "calculate",
                 "arguments": '{"expression":"1 + 1"}'},
            ]})
        return Response({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{}"}]},
        ]})

    model = OpenAIModel(post=post, timeout_seconds=17)
    assert model("answer", "prompt", {}, {},
                 calculator=lambda _: {"value": "2"},
                 remaining_seconds=lambda: 50 - now[0]) == "{}"
    assert timeouts == [17, 17]


def test_research_never_receives_answer_calculator_even_if_supplied(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return Response({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{}"}]},
        ]})

    assert OpenAIModel(post=post)("research", "prompt", {}, {},
                                    calculator=lambda _: {"ok": True}) == "{}"
    assert "tools" not in calls[0]
