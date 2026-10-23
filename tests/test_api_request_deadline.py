"""Offline API body deadlines and their ordinary installation dependencies."""
import socket
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
import requests
from packaging.requirements import Requirement
from urllib3.connection import HTTPConnection
from urllib3.response import HTTPResponse

from scryraven import model as model_module
from scryraven.chatgpt_plan import http
from scryraven.model import ModelError, OpenAIModel, built_in_model_config


@pytest.mark.parametrize("version,accepted", [
    ("2.5.0", False), ("2.6.0", True), ("3.0.0", False),
])
def test_base_requirements_enforce_shared_watchdog_compatibility(version, accepted):
    requirements = [
        Requirement(line) for line in
        (Path(__file__).resolve().parents[1] / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    dependency, = (item for item in requirements if item.name == "urllib3")
    assert (version in dependency.specifier) is accepted


def test_watchdog_uses_real_urllib3_response_shutdown(monkeypatch):
    shutdowns = []
    response = requests.Response()
    response.raw = HTTPResponse(
        connection=HTTPConnection("offline.invalid"), preload_content=False,
        sock_shutdown=shutdowns.append,
    )
    assert callable(response.raw.shutdown)

    class Timer:
        def __init__(self, seconds, callback):
            self.callback = callback
        def start(self):
            self.callback()
        def cancel(self):
            pass
        def join(self):
            pass

    monkeypatch.setattr(http.threading, "Timer", Timer)
    try:
        with pytest.raises(ModelError, match="^model_request_timed_out$"):
            with http.response_deadline(response, 1):
                assert shutdowns == [socket.SHUT_RD]
    finally:
        response.close()


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
