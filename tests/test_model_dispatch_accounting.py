"""Offline physical accounting at the actual model POST boundary."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import requests

from scryraven import model as model_module
from scryraven.chatgpt_plan import transport as plan_module
from scryraven.chatgpt_plan.http import PlanError
from scryraven.model import ModelConfig, ModelError, ModelRole, OpenAIModel
from scryraven.research import RunLimits, _Budget

CONFIG = ModelConfig(ModelRole("offline-research", "high"), ModelRole("offline-answer", "high"))


class Response:
    def __init__(self, body):
        self.body, self.closed = body, False
        self.status_code = 200
        self.headers = {"Content-Type": "text/event-stream"}
        self.raw = SimpleNamespace(shutdown=lambda: None)

    def raise_for_status(self):
        pass

    def json(self):
        return self.body

    def iter_content(self, chunk_size):
        event = {"type": "response.completed", "response": self.body}
        yield ("data: " + json.dumps(event) + "\n\n").encode()

    def close(self):
        self.closed = True


def completed(payload):
    return {"model": payload["model"], "status": "completed", "output": [{
        "id": "offline-final", "type": "message", "role": "assistant", "phase": "final_answer",
        "content": [{"type": "output_text", "text": "{}"}],
    }], "usage": {"input_tokens": 10, "output_tokens": 3}}


class OfflineAuth:
    """Explicit fake auth and HTTP; no real credential or network operations."""

    def __init__(self, *, access=None, failure=None):
        self.access_action, self.failure = access, failure
        self.access_calls, self.posts, self.responses = [], [], []
        self.http = self

    def access(self, account, *, timeout):
        self.access_calls.append((account, timeout))
        if self.access_action is not None:
            return self.access_action()
        return {"access_token": "offline-only-placeholder"}

    def request(self, method, url, **kwargs):
        assert method == "POST" and url == "https://api.openai.com/v1/responses"
        self.posts.append(kwargs)
        if self.failure is not None:
            raise self.failure
        response = Response(completed(kwargs["json"]))
        self.responses.append(response)
        return response


@pytest.fixture
def clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(model_module, "monotonic", lambda: now[0])

    class Deadline:
        def __init__(self, seconds):
            self.end = now[0] + seconds

        def left(self):
            left = self.end - now[0]
            if left <= 0:
                raise PlanError("model_request_timed_out")
            return left

    monkeypatch.setattr(plan_module, "Deadline", Deadline)
    return now


def budget(clock, *, seconds=30):
    return _Budget(RunLimits(seconds=seconds), lambda: clock[0])


def assert_no_dispatch(model, shared, usage, posts):
    assert not posts and not usage
    assert shared.physical == 0 and shared.roles == {"answer": 0, "research": 0}
    if model.plan_transport is not None:
        assert model.plan_transport.physical_requests == 0


@pytest.mark.parametrize("stage", ["research", "answer"])
def test_plan_auth_failure_never_counts_a_model_request(clock, stage):
    def fail_access():
        raise PlanError("model_authentication_failed")

    auth, usage, shared = OfflineAuth(access=fail_access), [], budget(clock)
    model = OpenAIModel(CONFIG, backend="chatgpt_plan", plan_auth=auth, usage_observer=usage.append)
    with pytest.raises(ModelError, match="^model_authentication_failed$"):
        model(stage, "offline", {}, {}, before_request=shared.before_model,
              remaining_seconds=lambda: shared.remaining_seconds)
    assert len(auth.access_calls) == 1
    assert_no_dispatch(model, shared, usage, auth.posts)


@pytest.mark.parametrize("expired_clock", ["request", "whole_turn"])
def test_plan_auth_can_exhaust_request_or_shared_clock_without_a_post(clock, expired_clock):
    turn_clock = clock if expired_clock == "request" else [0.0]
    shared, usage = budget(turn_clock), []

    def delayed_access():
        if expired_clock == "request":
            clock[0] = 6
        else:
            turn_clock[0] = 31
        return {"access_token": "offline-only-placeholder"}

    auth = OfflineAuth(access=delayed_access)
    model = OpenAIModel(CONFIG, backend="chatgpt_plan", plan_auth=auth,
                        timeout_seconds=5, usage_observer=usage.append)
    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        model("answer", "offline", {}, {}, before_request=shared.before_model,
              remaining_seconds=lambda: shared.remaining_seconds)
    assert_no_dispatch(model, shared, usage, auth.posts)


def test_plan_auth_rechecks_shorter_shared_remainder_before_post(clock):
    turn_clock, usage = [0.0], []
    shared = budget(turn_clock)

    def delayed_access():
        clock[0] = 2
        turn_clock[0] = 27
        return {"access_token": "offline-only-placeholder"}

    auth = OfflineAuth(access=delayed_access)
    model = OpenAIModel(CONFIG, backend="chatgpt_plan", plan_auth=auth, usage_observer=usage.append)
    assert model("answer", "offline", {}, {}, before_request=shared.before_model,
                 remaining_seconds=lambda: shared.remaining_seconds) == "{}"
    assert auth.access_calls == [("personal", 30)]
    assert len(auth.posts) == shared.physical == model.plan_transport.physical_requests == len(usage) == 1
    assert auth.posts[0]["timeout"] == 3
    assert shared.roles == {"answer": 1, "research": 0}
    assert usage[0].input_tokens == 10 and usage[0].output_tokens == 3
    assert auth.responses[0].closed


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_budget_denial_preserves_original_exception_without_dispatch_or_usage(monkeypatch, clock, backend):
    shared, usage, posts = budget(clock), [], []
    denied = RuntimeError("offline budget denial")

    def deny(_stage):
        raise denied

    def post(_url, **kwargs):
        posts.append(kwargs)
        pytest.fail("Denied model POST executed")

    auth = OfflineAuth()
    if backend == "api":
        monkeypatch.setenv("OPENAI_API_KEY", "offline-only-placeholder")
    model = OpenAIModel(CONFIG, backend=backend, post=post,
                        plan_auth=auth if backend == "chatgpt_plan" else None,
                        usage_observer=usage.append)
    with pytest.raises(RuntimeError) as error:
        model("answer", "offline", {}, {}, before_request=deny,
              remaining_seconds=lambda: shared.remaining_seconds)
    assert error.value is denied
    assert_no_dispatch(model, shared, usage, auth.posts if backend == "chatgpt_plan" else posts)


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
@pytest.mark.parametrize("stage", ["research", "answer"])
@pytest.mark.parametrize("failure,code", [
    (requests.Timeout("offline POST timeout"), "model_request_timed_out"),
    (requests.ConnectionError("offline POST failure"), "model_transport_failed"),
])
def test_attempted_post_failure_counts_once_with_unknown_usage(monkeypatch, clock, backend, stage, failure, code):
    shared, usage, posts = budget(clock), [], []

    def post(_url, **kwargs):
        posts.append(kwargs)
        raise failure

    auth = OfflineAuth(failure=failure)
    if backend == "api":
        monkeypatch.setenv("OPENAI_API_KEY", "offline-only-placeholder")
    model = OpenAIModel(CONFIG, backend=backend, post=post,
                        plan_auth=auth if backend == "chatgpt_plan" else None,
                        usage_observer=usage.append)
    with pytest.raises(ModelError, match=f"^{code}$"):
        model(stage, "offline", {}, {}, before_request=shared.before_model,
              remaining_seconds=lambda: shared.remaining_seconds)
    actual_posts = auth.posts if backend == "chatgpt_plan" else posts
    assert len(actual_posts) == shared.physical == len(usage) == 1
    assert shared.roles == {"answer": int(stage == "answer"), "research": int(stage == "research")}
    if model.plan_transport is not None:
        assert model.plan_transport.physical_requests == 1
    assert usage[0].stage == stage and usage[0].continuation_index == 0
    assert usage[0].input_tokens is None and usage[0].output_tokens is None


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
@pytest.mark.parametrize("stage", ["research", "answer"])
def test_successful_post_preserves_single_request_and_role_accounting(monkeypatch, clock, backend, stage):
    shared, usage, posts, responses = budget(clock), [], [], []

    def post(_url, **kwargs):
        posts.append(kwargs)
        response = Response(completed(kwargs["json"]))
        responses.append(response)
        return response

    auth = OfflineAuth()
    if backend == "api":
        monkeypatch.setenv("OPENAI_API_KEY", "offline-only-placeholder")
    model = OpenAIModel(CONFIG, backend=backend, post=post,
                        plan_auth=auth if backend == "chatgpt_plan" else None,
                        usage_observer=usage.append)
    assert model(stage, "offline", {}, {}, before_request=shared.before_model,
                 remaining_seconds=lambda: shared.remaining_seconds) == "{}"
    actual_posts = auth.posts if backend == "chatgpt_plan" else posts
    actual_responses = auth.responses if backend == "chatgpt_plan" else responses
    assert len(actual_posts) == shared.physical == len(usage) == 1
    assert shared.roles == {"answer": int(stage == "answer"), "research": int(stage == "research")}
    if model.plan_transport is not None:
        assert model.plan_transport.physical_requests == 1
    assert usage[0].stage == stage and usage[0].continuation_index == 0
    assert usage[0].input_tokens == 10 and usage[0].output_tokens == 3
    assert actual_responses[0].closed


def test_missing_api_configuration_has_no_dispatch_or_usage(monkeypatch, clock):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    shared, usage, posts = budget(clock), [], []
    model = OpenAIModel(CONFIG, post=lambda *_args, **kwargs: posts.append(kwargs), usage_observer=usage.append)
    with pytest.raises(ModelError, match="^model_configuration_missing$"):
        model("answer", "offline", {}, {}, before_request=shared.before_model)
    assert_no_dispatch(model, shared, usage, posts)


def test_plan_header_preparation_failure_has_no_dispatch_or_usage(clock):
    auth, shared, usage = OfflineAuth(access=lambda: {}), budget(clock), []
    model = OpenAIModel(CONFIG, backend="chatgpt_plan", plan_auth=auth, usage_observer=usage.append)
    with pytest.raises(ModelError, match="^model_transport_failed$"):
        model("answer", "offline", {}, {}, before_request=shared.before_model,
              remaining_seconds=lambda: shared.remaining_seconds)
    assert_no_dispatch(model, shared, usage, auth.posts)
