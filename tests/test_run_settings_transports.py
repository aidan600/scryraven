"""Controlled Responses transports: exact settings, strict contracts and custody."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest
import requests
from test_image_inputs import answer, decision, image_blocks, reply, session_image
from test_model_transport import Response
from test_production_plan_transport import FrozenAuth, Reply

from scryraven.model import ModelConfig, ModelError, ModelRole, OpenAIModel, valid_model_identifier
from scryraven.research import _run_turn


def config(backend="api", effort="medium", tier="default"):
    prefix = "openai/" if backend == "openrouter" else ""
    return ModelConfig(ModelRole(prefix + "gpt-6.1-terra", effort, tier),
                       ModelRole(prefix + "gpt-6.1-sol", effort, tier))


@pytest.mark.parametrize("backend,variable,url", [
    ("api", "OPENAI_API_KEY", "https://api.openai.com/v1/responses"),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/responses"),
])
@pytest.mark.parametrize("effort", [None, "none", "low", "medium", "high", "xhigh", "max"])
def test_exact_paid_backend_identifier_reasoning_endpoint_and_credential(monkeypatch, backend, variable, url, effort):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-openai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    calls = []

    def post(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        return Response(reply({}))

    model = OpenAIModel(config(backend, effort), backend=backend, post=post)
    model.validate_configuration()
    assert model("answer", "prompt", {}, {}) == "{}"
    endpoint, request = calls[0]
    assert endpoint == url and request["allow_redirects"] is False
    assert request["headers"] == {"Authorization": "Bearer " + ("offline-router" if backend == "openrouter" else "offline-openai")}
    payload = request["json"]
    assert payload["model"] == model.config.answer.model
    assert payload.get("reasoning") == ({"effort": effort} if effort else None)
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["type"] == "json_schema" and payload["store"] is False
    if backend == "openrouter":
        assert payload["provider"] == {"require_parameters": True, "allow_fallbacks": False}
        assert payload["plugins"] == payload["transforms"] == []
        assert not {"models", "route", "service_tier", "prompt_cache_key", "prompt_cache_options"} & payload.keys()
        assert not any("prompt_cache_breakpoint" in block for item in payload["input"] for block in item.get("content", []))


@pytest.mark.parametrize("tier", ["default", "fast"])
def test_explicit_standard_fast_receipts_do_not_infer_returned_tier(monkeypatch, tier):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-openai")
    observed, calls = [], []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return Response({**reply({}), "model": "gpt-6.1-sol", "service_tier": "default"})

    model = OpenAIModel(config(tier=tier), post=post, usage_observer=observed.append)
    assert model("answer", "prompt", {}, {}) == "{}" and len(calls) == 1
    assert calls[0]["service_tier"] == tier
    assert observed[0].requested_service_tier == tier and observed[0].returned_service_tier == "default"
    assert observed[0].backend == "api" and observed[0].returned_model == "gpt-6.1-sol"


@pytest.mark.parametrize("backend,missing,other", [
    ("api", "OPENAI_API_KEY", "OPENROUTER_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY", "OPENAI_API_KEY"),
])
def test_missing_credential_never_uses_other_backend(monkeypatch, backend, missing, other):
    monkeypatch.delenv(missing, raising=False)
    monkeypatch.setenv(other, "offline-other-provider")
    model = OpenAIModel(config(backend), backend=backend,
                        post=lambda *a, **k: pytest.fail("Inference must not dispatch"))
    with pytest.raises(ModelError, match="^model_configuration_missing$"):
        model.validate_configuration()
    with pytest.raises(ModelError, match="^model_configuration_missing$"):
        model("answer", "prompt", {}, {})


@pytest.mark.parametrize("identifier", ["https://evil.test/responses", "openai/gpt:online", "openrouter/auto",
    "openai/gpt:free", "openai/gpt/nested", "openai/gpt?url=x", "openai/gpt#x", "openai/gpt x",
    "openai/gpt\n", "openai/$(run)", "openai/gpt;cmd", "x" * 201, "", "../model"])
def test_identifier_data_cannot_select_routes_or_instructions(monkeypatch, identifier):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    assert not valid_model_identifier(identifier, "openrouter")
    model = OpenAIModel(ModelConfig(ModelRole(identifier, None), ModelRole(identifier, None)),
                        backend="openrouter", post=lambda *a, **k: pytest.fail("Invalid identifier dispatched"))
    with pytest.raises(ModelError, match="^model_identifier_invalid$"):
        model("answer", "prompt", {}, {})


def test_plan_clone_reuses_auth_and_omits_api_parameters(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    auth = FrozenAuth(Reply("answer", {}))
    original = OpenAIModel(config(tier="fast"), backend="chatgpt_plan", plan_auth=auth)
    cloned = original.with_config(config(effort=None))
    assert cloned is not original and cloned.plan_transport.auth is auth
    assert cloned("answer", "prompt", {}, {}) == "{}"
    payload, = auth.calls
    assert "reasoning" not in payload and "service_tier" not in payload
    assert "max_output_tokens" not in payload and "prompt_cache_key" not in payload
    api = original.with_config(config(), backend="api")
    assert api.plan_transport is None and api.backend == "api"


def test_plan_account_catalog_exact_model_and_effort_preflight_without_inference():
    calls = []

    def catalog(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return {"models": [
            {"slug": "gpt-6.1-terra", "visibility": "list", "display_name": "Terra",
             "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}]},
            {"slug": "gpt-6.1-sol", "visibility": "list", "display_name": "Sol"},
            {"slug": "hidden", "visibility": "hide", "display_name": "Hidden"},
        ]}

    auth = SimpleNamespace(access=lambda *a, **k: {"access_token": "offline-plan"},
                           http=SimpleNamespace(json=catalog))
    model = OpenAIModel(config(), backend="chatgpt_plan", plan_auth=auth)
    rows = model.plan_catalog()
    assert [item["slug"] for item in rows] == ["gpt-6.1-terra", "gpt-6.1-sol"]
    assert "offline-plan" not in repr(rows)
    assert calls[0][0:2] == ("GET", "https://api.openai.com/v1/models")
    model.validate_configuration(catalog=rows)
    assert len(calls) == 1
    with pytest.raises(ModelError, match="^model_reasoning_unsupported$"):
        model.with_config(config(effort="xhigh")).validate_configuration(catalog=rows)
    with pytest.raises(ModelError, match="^model_unavailable$"):
        model.with_config(ModelConfig(ModelRole("missing", None), model.config.answer)).validate_configuration(catalog=rows)


def test_openrouter_continuation_preserves_strict_tools_and_opaque_history(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    calls, observed = [], []
    opaque = {"type": "reasoning", "id": "rs_1", "encrypted_content": "opaque-offline"}
    function = {"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": "calculate",
                "arguments": '{"expression":"12 - 4"}'}
    replies = iter([
        {"status": "completed", "output": [opaque, function], "model": "openai/gpt-6.1-sol"},
        {**reply({"answer": "8"}), "model": "openai/gpt-6.1-sol", "provider": "OpenAI",
         "usage": {"input_tokens": 10, "output_tokens": 3, "cost": 0.00012}},
    ])

    def post(url, **kwargs):
        calls.append(deepcopy(kwargs["json"]))
        assert url == "https://openrouter.ai/api/v1/responses"
        return Response(next(replies))

    model = OpenAIModel(config("openrouter"), backend="openrouter", post=post, usage_observer=observed.append)
    assert model("answer", "prompt", {}, {}, calculator=lambda _: {"value": "8"}) == '{"answer": "8"}'
    assert len(calls) == 2 and calls[1]["input"][-3:-1] == [opaque, function]
    assert calls[1]["input"][-1]["call_id"] == "call_1"
    for payload in calls:
        assert payload["tools"][0]["strict"] is True
        assert payload["include"] == ["reasoning.encrypted_content"]
        assert payload["text"]["format"]["strict"] is True and "previous_response_id" not in payload
    assert observed[1].provider == "OpenAI" and observed[1].reported_cost_usd == 0.00012
    assert "opaque-offline" not in json.dumps([asdict(item) for item in observed])


@pytest.mark.parametrize("failure", ["http", "server_tool", "bad_arguments", "bad_final"])
def test_openrouter_incompatibility_stops_without_paid_repair_or_fallback(monkeypatch, failure):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        if failure == "http":
            response = requests.Response()
            response.status_code = 400
            raise requests.HTTPError("private-provider-data", response=response)
        if failure == "server_tool":
            return Response({"status": "completed", "output": [{"type": "openrouter:web_search"}]})
        if failure == "bad_arguments":
            return Response({"status": "completed", "output": [{"type": "function_call", "call_id": "bad",
                             "name": "calculate", "arguments": "{}"}]})
        return Response(reply({"wrong": "schema"}))

    model = OpenAIModel(config("openrouter"), backend="openrouter", post=post)
    with pytest.raises(ModelError, match="^model_contract_incompatible$"):
        model("answer", "prompt", {}, {}, calculator=lambda _: pytest.fail("Invalid tool executed"),
              final_feedback=lambda _: {"code": "malformed_model_response"})
    assert len(calls) == 1


def test_openai_malformed_feedback_dictionary_preserves_native_history_for_one_correction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-openai")
    calls, feedbacks = [], []
    opaque = {"type": "reasoning", "id": "offline-reasoning", "encrypted_content": "opaque-kept-context"}
    function = {"type": "function_call", "name": "calculate", "call_id": "native-calculation",
                "arguments": '{"expression":"12 - 4"}'}
    outputs = iter([{"status": "completed", "output": [opaque, function]},
                    reply({"invalid": "REJECTED FINAL CLAIM"}), reply({"answer": "8"})])

    def post(_url, **kwargs):
        calls.append(deepcopy(kwargs["json"]))
        return Response(next(outputs))

    def feedback(raw):
        feedbacks.append(raw)
        return None if json.loads(raw) == {"answer": "8"} else {"code": "malformed_model_response"}

    model = OpenAIModel(config(), backend="api", post=post)
    assert model("answer", "prompt", {}, {}, calculator=lambda _: {"value": "8"}, final_feedback=feedback) == '{"answer": "8"}'
    assert len(calls) == 3 and len(feedbacks) == 2
    assert calls[-1]["input"][:len(calls[-2]["input"])] == calls[-2]["input"]
    assert opaque in calls[-1]["input"] and function in calls[-1]["input"]
    assert any(item.get("type") == "function_call_output" and item.get("call_id") == "native-calculation"
               for item in calls[-1]["input"])
    assert "malformed_model_response" in json.dumps(calls[-1]["input"][-1])
    assert "REJECTED FINAL CLAIM" not in json.dumps(calls)
    assert all(payload["store"] is False and "previous_response_id" not in payload for payload in calls)


def test_openrouter_reported_model_mismatch_cannot_publish_as_selected_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    observed, calls = [], []

    def post(_url, **kwargs):
        calls.append(kwargs["json"])
        return Response({**reply({"answer": "8"}), "model": "openai/a-different-model"})

    model = OpenAIModel(config("openrouter"), backend="openrouter", post=post, usage_observer=observed.append)
    with pytest.raises(ModelError, match="^model_routing_mismatch$"):
        model("answer", "prompt", {}, {})
    assert len(calls) == 1 and observed[0].returned_model == "openai/a-different-model"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, "0.12", 10 ** 1000])
def test_openrouter_invalid_reported_cost_remains_unknown(monkeypatch, value):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    observed = []
    model = OpenAIModel(config("openrouter"), backend="openrouter", usage_observer=observed.append,
                        post=lambda *a, **k: Response({**reply({}), "usage": {"cost": value}}))
    assert model("answer", "prompt", {}, {}) == "{}"
    assert observed[0].reported_cost_usd is None


@pytest.mark.parametrize("retained", [False, True])
def test_openrouter_images_and_retained_image_inspection_keep_real_content(monkeypatch, retained):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-router")
    calls = []
    read = {"kind": "read", "target": "I1", "focus": "", "mode": "local",
            "start_char": None, "end_char": None}
    outputs = iter([reply(decision([read])), reply(decision()), reply(answer())] if retained
                   else [reply(decision()), reply(answer())])

    def post(_url, **kwargs):
        calls.append(deepcopy(kwargs["json"]))
        return Response(next(outputs))

    result = _run_turn("Describe the supplied shapes", images=(session_image(),),
                       image_ids=() if retained else ("I1",),
                       model=OpenAIModel(config("openrouter"), backend="openrouter", post=post),
                       search=lambda _: pytest.fail("Image observation acquired external material"))
    assert result.image_ids == ("I1",) and not result.citations
    assert [len(image_blocks(payload)) for payload in calls] == ([0, 1, 1] if retained else [1, 1])
