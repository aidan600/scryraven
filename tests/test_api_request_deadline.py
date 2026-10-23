"""API body reads share the physical-request ceiling; all transports are synthetic."""
from threading import Event
from types import SimpleNamespace

import pytest
import requests

from scryraven import model as model_module
from scryraven.chatgpt_plan import http
from scryraven.model import ModelError, OpenAIModel, built_in_model_config


class Response:
    def __init__(self, read):
        self.read = read
        self.closed = False
        self.stopped = Event()
        self.raw = SimpleNamespace(shutdown=self.stopped.set)

    def raise_for_status(self):
        pass

    def json(self):
        return self.read(self)

    def close(self):
        self.closed = True


@pytest.mark.parametrize("stage", ["research", "answer"])
def test_watchdog_interrupts_silent_api_body_and_counts_one_request(monkeypatch, stage):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-key")
    calls, usage, physical = [], [], []

    def blocked(response):
        assert response.stopped.wait(timeout=2)
        raise requests.ConnectionError("synthetic interrupted body")

    response = Response(blocked)

    def post(_url, **kwargs):
        calls.append(kwargs)
        return response

    model = OpenAIModel(built_in_model_config(), post=post, timeout_seconds=0.03,
                        usage_observer=usage.append)
    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        model(stage, "synthetic", {}, {}, remaining_seconds=lambda: 10,
              before_request=physical.append)
    assert len(calls) == len(usage) == 1 and physical == [stage]
    assert calls[0]["stream"] is True and calls[0]["timeout"].total == 0.03
    assert response.closed and response.stopped.is_set()
    assert usage[0].input_tokens is None and usage[0].output_tokens is None


def test_header_time_is_subtracted_from_body_watchdog_and_turn_remaining(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-key")
    now, watchdog_seconds, calls = [0.0], [], []
    monkeypatch.setattr(model_module, "monotonic", lambda: now[0])

    class Timer:
        def __init__(self, seconds, callback):
            watchdog_seconds.append(seconds)
            self.callback = callback
        def start(self):
            pass
        def cancel(self):
            pass
        def join(self):
            pass

    monkeypatch.setattr(http.threading, "Timer", Timer)
    response = Response(lambda _: {"status": "completed", "output": [{"type": "message",
        "content": [{"type": "output_text", "text": "{}"}]}]})

    def post(_url, **kwargs):
        calls.append(kwargs)
        now[0] += 2
        return response

    model = OpenAIModel(built_in_model_config(), post=post, timeout_seconds=20)
    assert model("research", "synthetic", {}, {}, remaining_seconds=lambda: 3) == "{}"
    assert calls[0]["timeout"].total == 3
    assert calls[0]["timeout"].connect_timeout == 3
    assert watchdog_seconds == [1]
    assert response.closed


def test_headers_that_exhaust_remaining_turn_never_read_or_publish_body(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-offline-key")
    now, reads = [0.0], []
    monkeypatch.setattr(model_module, "monotonic", lambda: now[0])
    response = Response(lambda _: reads.append("body"))

    def post(_url, **kwargs):
        now[0] += 4
        return response

    model = OpenAIModel(built_in_model_config(), post=post)
    with pytest.raises(ModelError, match="^model_request_timed_out$"):
        model("answer", "synthetic", {}, {}, remaining_seconds=lambda: 3)
    assert reads == [] and response.closed
