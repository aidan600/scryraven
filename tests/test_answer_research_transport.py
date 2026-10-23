"""Synthetic nested transport checks; no authentication or live model inference."""
from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
import requests

from scryraven import model as transport
from scryraven.model import ModelConfig, ModelError, ModelRole, OpenAIModel, capture_model_usage

CONFIG = ModelConfig(ModelRole("research-test", "high"), ModelRole("answer-test", "medium"))


def final(text="{}"):
    return {"type": "message", "role": "assistant", "phase": "final_answer",
            "content": [{"type": "output_text", "text": text}]}


def call(name="research", identity="r1", arguments='{"need":"Find the governing rule"}'):
    return {"type": "function_call", "name": name, "call_id": identity, "arguments": arguments}


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def scripted_model(monkeypatch, backend, script, **options):
    """Exercise the shared dispatch plus the real plan payload adapter."""
    calls = []
    replies = iter(script)

    def dispatch(payload, timeout):
        calls.append((deepcopy(payload), timeout))
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return {"status": "completed", "output": reply,
                "usage": {"input_tokens": 10, "output_tokens": 2}}

    if backend == "api":
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-only")

        def post(_url, **kwargs):
            return Response(dispatch(kwargs["json"], kwargs["timeout"].total))

        model = OpenAIModel(CONFIG, post=post, **options)
    else:
        from scryraven.chatgpt_plan.transport import plan_payload

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        model = OpenAIModel(CONFIG, backend="chatgpt_plan", **options)
        def plan_request(payload, *, timeout, before_dispatch):
            body = plan_payload(payload)
            return dispatch(body, min(timeout, before_dispatch()))

        model.plan_transport = SimpleNamespace(request=plan_request)
    return model, calls


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_nested_research_resumes_owner_with_opaque_items_and_separate_usage(monkeypatch, backend):
    opaque = {"type": "reasoning", "id": "owner-reason", "encrypted_content": "synthetic-opaque-owner"}
    script = [[opaque, call()], [final('{"found":true}')],
              [call("calculate", "c1", '{"expression":"7*2"}'),
               call("library_read", "l1", '{"target":"E1"}')], [final('{"answer":"14 [E1]"}')]]
    all_usage, owner_usage, research_usage, dispatched = [], [], [], []
    model, calls = scripted_model(monkeypatch, backend, script, usage_observer=all_usage.append)
    snapshots = []

    def research(raw):
        assert json.loads(raw) == {"need": "Find the governing rule"}
        with capture_model_usage(research_usage.append):
            value = model("research", "investigate only this need", {"question": "immutable", "need": raw}, {},
                          before_request=dispatched.append, remaining_seconds=lambda: 700)
        assert json.loads(value) == {"found": True}
        return {"evidence": [{"id": "E1", "content": "The governing value is seven."}]}

    def snapshot():
        snapshots.append(len(dispatched))
        return {"physical_remaining": 40 - len(dispatched)}

    with capture_model_usage(owner_usage.append):
        result = model("answer", "own the whole question", {"question": "immutable"}, {},
                       research_tool=research, calculator=lambda _: {"value": "14"},
                       answer_library=lambda *_: {"evidence": [{"id": "E1", "content": "seven"}]},
                       before_request=dispatched.append, resource_snapshot=snapshot,
                       remaining_seconds=lambda: 800)
    assert json.loads(result) == {"answer": "14 [E1]"}
    assert dispatched == ["answer", "research", "answer", "answer"]
    assert [item.stage for item in all_usage] == dispatched
    assert [item.stage for item in owner_usage] == ["answer"] * 3
    assert [item.stage for item in research_usage] == ["research"]
    assert [item.continuation_index for item in owner_usage] == [0, 1, 2]
    assert [item.continuation_index for item in research_usage] == [0]
    assert owner_usage[0].input_characters < owner_usage[1].input_characters < owner_usage[2].input_characters
    assert [item.input_characters for item in all_usage] == [
        len(json.dumps(payload["input"], ensure_ascii=False, sort_keys=True)) for payload, _ in calls]
    assert snapshots == [2, 3]
    assert model.timeout_seconds == 300
    assert [entry[0]["model"] for entry in calls] == ["answer-test", "research-test", "answer-test", "answer-test"]
    assert "synthetic-opaque-owner" not in json.dumps(calls[1][0])
    assert opaque in calls[2][0]["input"] and opaque in calls[3][0]["input"]
    tool_results = [item for item in calls[3][0]["input"] if item.get("type") == "function_call_output"]
    assert [item["call_id"] for item in tool_results] == ["r1", "c1", "l1"]
    assert json.loads(tool_results[0]["output"])["evidence"][0]["id"] == "E1"
    assert any("physical_remaining" in json.dumps(item) for item in calls[2][0]["input"] if item.get("role") == "developer")
    tools = calls[0][0].get("tools") or next(item["tools"] for item in calls[0][0]["input"] if item.get("type") == "additional_tools")
    research_schema = next(item for item in tools if item["name"] == "research")
    assert research_schema["strict"] is True
    assert research_schema["parameters"]["additionalProperties"] is False
    assert research_schema["parameters"]["required"] == ["need"]
    assert "tools" not in calls[1][0]
    assert not any(item.get("type") == "additional_tools" for item in calls[1][0]["input"])


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
@pytest.mark.parametrize("arguments", ["bad-json", "{}", '{"need":""}', '{"need":"  "}',
                                      '{"need":"a","other":true}', '{"need":"a","need":"b"}',
                                      json.dumps({"need": "x" * 8001})])
def test_research_argument_errors_continue_without_dispatching_investigator(monkeypatch, backend, arguments):
    model, calls = scripted_model(monkeypatch, backend, [[call(arguments=arguments)], [final()]])
    model("answer", "instructions", {}, {}, research_tool=lambda _: pytest.fail("invalid delegation executed"))
    output = next(item for item in calls[1][0]["input"] if item.get("type") == "function_call_output")
    assert json.loads(output["output"]) == {"error": "invalid_tool_arguments"}


@pytest.mark.parametrize("bad_calls", [
    [call("unknown")], [call(), call()],
    [call(), {**call(identity="r2"), "namespace": "unauthorized"}],
    [call(), {**call(identity="r2"), "arguments": {"need": "not serialized"}}],
])
def test_entire_multi_tool_envelope_is_validated_before_any_tool_executes(monkeypatch, bad_calls):
    model, _ = scripted_model(monkeypatch, "api", [bad_calls])
    with pytest.raises(ModelError, match="^malformed_model_response$"):
        model("answer", "instructions", {}, {}, research_tool=lambda _: pytest.fail("invalid envelope executed"))


def test_duplicate_tool_identity_across_continuations_is_rejected(monkeypatch):
    model, _ = scripted_model(monkeypatch, "api", [[call()], [call()]])
    invocations = []
    with pytest.raises(ModelError, match="^malformed_model_response$"):
        model("answer", "instructions", {}, {}, research_tool=lambda raw: invocations.append(raw) or {})
    assert len(invocations) == 1


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_shared_before_request_runs_once_for_failure_and_denies_undispatched_continuation(monkeypatch, backend):
    model, calls = scripted_model(monkeypatch, backend, [requests.Timeout("private detail")])
    dispatched, usage = [], []
    with capture_model_usage(usage.append), pytest.raises(ModelError, match="^model_request_timed_out$"):
        model("research", "instructions", {}, {}, before_request=dispatched.append, remaining_seconds=lambda: 21)
    assert dispatched == ["research"] and len(calls) == len(usage) == 1
    assert calls[0][1] == 21
    assert usage[0].input_tokens is None

    model, calls = scripted_model(monkeypatch, backend, [[call()], [final()]])

    class Limit(Exception):
        pass

    def limited(stage):
        if dispatched == ["answer"]:
            raise Limit()
        dispatched.append(stage)

    dispatched.clear()
    with pytest.raises(Limit):
        model("answer", "instructions", {}, {}, research_tool=lambda _: {}, before_request=limited)
    assert dispatched == ["answer"] and len(calls) == 1


@pytest.mark.parametrize("stage", ["research", "answer"])
@pytest.mark.parametrize("configured,remaining,expected", [(900, 800, 300), (17, 800, 17), (300, 6, 6)])
def test_all_roles_share_remaining_time_and_operational_request_ceiling(monkeypatch, stage, configured, remaining, expected):
    model, calls = scripted_model(monkeypatch, "api", [[final()]], timeout_seconds=configured)
    model(stage, "instructions", {}, {}, remaining_seconds=lambda: remaining)
    assert calls[0][1] == expected
    assert model.timeout_seconds == configured


def test_elapsed_whole_turn_prevents_next_tool_or_request(monkeypatch):
    remaining = [10]
    model, calls = scripted_model(monkeypatch, "api", [[call()]])

    def research(_):
        remaining[0] = 0
        return {}

    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        model("answer", "instructions", {}, {}, research_tool=research, remaining_seconds=lambda: remaining[0])
    assert len(calls) == 1


def test_direct_tool_interaction_does_not_renew_its_clock(monkeypatch):
    now = [0]
    monkeypatch.setattr(transport, "monotonic", lambda: now[0])
    model, calls = scripted_model(monkeypatch, "api", [[call()], [final()]], timeout_seconds=12)

    def research(_):
        now[0] = 13
        return {}

    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        model("answer", "instructions", {}, {}, research_tool=research)
    assert len(calls) == 1


def test_research_role_cannot_receive_owner_tools_or_recurse(monkeypatch):
    model, calls = scripted_model(monkeypatch, "api", [[final()]])
    model("research", "instructions", {}, {}, research_tool=lambda _: {}, calculator=lambda _: {}, answer_library=lambda *_: {})
    assert "tools" not in calls[0][0]
