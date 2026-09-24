"""Mechanical Responses API checks, independent of specific models or prompts."""

from __future__ import annotations

import json

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


def test_split_defaults_preserve_independent_environment_overrides(monkeypatch):
    for role in ("FAST", "SMART"):
        for field in ("MODEL", "REASONING"):
            monkeypatch.delenv(f"SCRYRAVEN_{role}_{field}", raising=False)
    expected = ModelConfig(ModelRole("gpt-6-luna", "high"), ModelRole("gpt-6-sol", "medium"))
    assert ModelConfig() == expected
    assert ModelConfig.from_environment() == expected
    monkeypatch.setenv("SCRYRAVEN_FAST_MODEL", "configured-fast")
    monkeypatch.setenv("SCRYRAVEN_SMART_REASONING", "high")
    assert ModelConfig.from_environment() == ModelConfig(
        ModelRole("configured-fast", "high"), ModelRole("gpt-6-sol", "high"),
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
    assert [call[1]["json"]["model"] for call in calls] == [config.fast.model, config.smart.model]
    for url, kwargs in calls:
        assert url == "https://api.openai.com/v1/responses"
        payload = kwargs["json"]
        assert json.loads("".join(block["text"] for block in payload["input"][1]["content"])) == {"question": "test"}
        assert payload["text"]["format"]["schema"] == schema
        assert payload["text"]["format"]["strict"] is True
        assert payload["store"] is False
        assert "tools" not in payload
        if payload["model"] == config.fast.model:
            assert "reasoning" not in payload
        else:
            assert payload["reasoning"] == {"effort": config.smart.reasoning}


def test_environment_overrides_reach_their_stages(monkeypatch):
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
    assert [(call["model"], call["reasoning"]["effort"]) for call in calls] == [
        ("configured-research", "low"), ("configured-answer", "high"),
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


def test_unconfigured_service_tier_leaves_existing_request_shape(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    calls = []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return Response({"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "{}"}]},
        ]})

    OpenAIModel(ModelConfig(), post=post)("research", "prompt", {}, {})
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
