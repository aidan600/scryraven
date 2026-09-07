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

    config = ModelConfig(ModelRole("small-configured-model", "low"), ModelRole("strong-configured-model", "medium"))
    model = OpenAIModel(config, post=post)
    schema = {"type": "object", "additionalProperties": False, "properties": {}, "required": []}
    for stage in ("research", "analyst", "author"):
        assert model(stage, "instructions", {"question": "test"}, schema) == '{"answer":"ok"}'
    assert [call[1]["json"]["model"] for call in calls] == [config.fast.model, config.smart.model, config.fast.model]
    for url, kwargs in calls:
        assert url == "https://api.openai.com/v1/responses"
        payload = kwargs["json"]
        assert json.loads(payload["input"]) == {"question": "test"}
        assert payload["text"]["format"]["schema"] == schema
        assert payload["text"]["format"]["strict"] is True
        assert payload["store"] is False
        assert "tools" not in payload


@pytest.mark.parametrize("data,code", [
    ({"status": "incomplete", "output": []}, "model_response_incomplete"),
    ({"status": "completed", "output": []}, "model_response_empty"),
    ({"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "private details"}]}]}, "model_refused"),
    ({"status": "completed", "output": None}, "malformed_model_response"),
])
def test_provider_failures_do_not_expose_raw_payloads(monkeypatch, data, code):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    model = OpenAIModel(post=lambda *a, **k: Response(data))
    with pytest.raises(ModelError, match=f"^{code}$"):
        model("author", "private prompt", {}, {})

    def failed(*args, **kwargs):
        raise requests.ConnectionError("secret-bearing request detail")

    with pytest.raises(ModelError, match="^model_transport_failed$"):
        OpenAIModel(post=failed)("research", "prompt", {}, {})
