"""Production entrypoint parity with complete synthetic personal-plan streams.

These fixtures verify transport, custody and publication mechanics. They make no
network/authentication request and establish no live model competence.
"""
from __future__ import annotations

import copy
import json
import socket
from dataclasses import asdict, dataclass
from types import SimpleNamespace

import pytest
from test_research_loop import answer, decision, request

from core.exa_transport import DiscoveryCandidate
from core.transport import FetchedMaterial
from scryraven.answer_library import LIBRARY_TOOLS
from scryraven.errors import RunError
from scryraven.model import _CALCULATOR_TOOL, ModelError, OpenAIModel, built_in_model_config
from scryraven.research import ANSWER_PROMPT, RESEARCH_PROMPT, RunLimits, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

URL = "https://example.test/synthetic-transport-standard"
HIGHLIGHT = "The synthetic standard specifies seven units under sheltered conditions."
FULL_TEXT = HIGHLIGHT + "\n\nThe interval is eight cycles, including the initial inspection."
ENCRYPTED = "SYNTHETIC_ENCRYPTED_CONTINUATION_DO_NOT_PUBLISH"


def forbidden(*_args, **_kwargs):
    pytest.fail("Unexpected network, external provider or private authentication")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def packet(payload):
    return json.loads("".join(
        block.get("text", "") for message in payload["input"] if message.get("role") == "user"
        for block in message.get("content", [])
    ))


def usage(tokens=10):
    return {"input_tokens": tokens, "output_tokens": 5,
            "input_tokens_details": {"cached_tokens": 2, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 1}}


@dataclass
class Reply:
    stage: str
    value: object = None
    tool: str | None = None
    call_id: str = "calc_1"
    namespace: str | None = None
    headerless: bool = False
    empty_terminal: bool = False
    interrupted: bool = False
    status: str = "completed"
    counters: bool = True

    def stream(self, payload):
        assert payload["text"]["format"]["name"] == self.stage
        value = self.value(packet(payload)) if callable(self.value) else self.value
        if self.tool is not None:
            items = [{"id": "rs_1", "type": "reasoning", "summary": [], "encrypted_content": ENCRYPTED},
                     {"id": "fc_1", "type": "function_call", "name": "calculate", "call_id": self.call_id,
                      "arguments": json.dumps({"expression": self.tool}), "status": "completed"}]
            if self.namespace is not None:
                items[-1]["namespace"] = self.namespace
        else:
            items = [{"id": "msg_progress", "type": "message", "role": "assistant",
                      "phase": "commentary", "status": "completed",
                      "content": [{"type": "output_text", "text": "Synthetic progress only."}]},
                     {"id": "msg_final", "type": "message", "role": "assistant",
                      "phase": "final_answer", "status": "completed",
                      "content": [{"type": "output_text", "text": json.dumps(value)}]}]
        events = []
        for index, item in enumerate(items):
            if item["type"] == "message":
                initial = {**item, "status": "in_progress", "content": []}
                events.append({"type": "response.output_item.added", "output_index": index, "item": initial})
                text = item["content"][0]["text"]
                for delta in (text[:len(text) // 2], text[len(text) // 2:]):
                    events.append({"type": "response.output_text.delta", "output_index": index,
                                   "content_index": 0, "item_id": item["id"], "delta": delta})
                events.append({"type": "response.output_text.done", "output_index": index,
                               "content_index": 0, "item_id": item["id"], "text": text})
            events.append({"type": "response.output_item.done", "output_index": index, "item": item})
        if not self.interrupted:
            terminal = {"model": payload["model"], "status": self.status,
                        "output": [] if self.empty_terminal else items}
            if self.counters:
                terminal["usage"] = usage()
            if self.status == "incomplete":
                terminal["incomplete_details"] = {"reason": "max_output_tokens"}
            events.append({"type": "response." + self.status, "response": terminal})
        return Stream(events, headerless=self.headerless)


class Stream:
    def __init__(self, events, *, headerless=False):
        self.status_code = 200
        self.headers = {} if headerless else {"Content-Type": "text/event-stream; charset=utf-8"}
        self.events, self.closed = events, False
        self.raw = SimpleNamespace(shutdown=lambda: None)

    def iter_content(self, chunk_size):
        for event in self.events:
            yield ("data: " + json.dumps(event) + "\n\n").encode("utf-8")

    def close(self):
        self.closed = True


class FrozenAuth:
    def __init__(self, *replies):
        self.replies = iter(replies)
        self.calls, self.streams = [], []
        self.http = self

    def access(self, account, *, timeout):
        # Deadline subtraction may exceed 120 by one floating-point ULP when
        # the monotonic clock crosses an exponent boundary on a fresh CI host.
        assert account == "personal" and 0 < timeout <= 120 + 1e-9
        return {"access_token": "synthetic-plan-token"}

    def request(self, method, url, **kwargs):
        assert method == "POST" and url == "https://api.openai.com/v1/responses"
        assert kwargs["headers"]["Authorization"] == "Bearer synthetic-plan-token"
        assert kwargs["stream"] is True and 0 < kwargs["timeout"] <= 120 + 1e-9
        payload = copy.deepcopy(kwargs["json"])
        self.calls.append(payload)
        response = next(self.replies).stream(payload)
        self.streams.append(response)
        return response


def plan_model(*replies):
    auth = FrozenAuth(*replies)
    model = OpenAIModel(built_in_model_config(), backend="chatgpt_plan", plan_account="personal", plan_auth=auth)
    return model, auth


def search(_query, **_kwargs):
    return [DiscoveryCandidate("Synthetic public standard", URL, HIGHLIGHT, context_kind="provider_highlights")]


def test_plan_native_research_dependent_calculation_and_unknown_usage():
    final = answer("30 units from the stipulated amount.", support_basis="user_premises")
    model, auth = plan_model(
        Reply("research", decision("answer"), headerless=True, empty_terminal=True),
        Reply("answer", tool="100 * 1.2", call_id="calc_a", empty_terminal=True),
        Reply("answer", tool="120 / 4", call_id="calc_b"),
        Reply("answer", final, headerless=True, empty_terminal=True, counters=False),
    )
    reported = []
    model.usage_observer = reported.append
    result = run("If the amount is 100 units, increase it 20 percent and divide by four.",
                 model=model, search=forbidden, fetch=forbidden, lexical_search=forbidden,
                 limits=RunLimits(semantic_attempts=2))
    assert result.answer == final["answer"] and result.posture == "supported"
    assert result.evidence == result.citations == ()
    assert len(auth.calls) == 4 and all(stream.closed for stream in auth.streams)
    assert [p["model"] for p in auth.calls] == ["gpt-6-luna", *["gpt-6.1-sol"] * 3]
    assert [p["reasoning"]["effort"] for p in auth.calls] == ["high", "medium", "medium", "medium"]
    assert all(p["store"] is False and p["stream"] is True for p in auth.calls)
    assert all("max_output_tokens" not in p and "service_tier" not in p for p in auth.calls)
    assert not any(item.get("type") == "additional_tools" for item in auth.calls[0]["input"])
    for payload in auth.calls[1:]:
        assert "tools" not in payload
        extras = [(index, item) for index, item in enumerate(payload["input"])
                  if item.get("type") == "additional_tools"]
        assert len(extras) == 1 and extras[0][1] == {
            "type": "additional_tools", "role": "developer", "tools": [_CALCULATOR_TOOL, *LIBRARY_TOOLS]}
        first_return = next((index for index, item in enumerate(payload["input"])
                             if item.get("type") in {"reasoning", "function_call", "function_call_output"}),
                            len(payload["input"]))
        assert extras[0][0] < first_return
    assert auth.calls[0]["text"]["format"]["schema"]["properties"]["action"]["enum"] == ["research", "answer"]
    first_instructions = auth.calls[0]["input"][0]["content"][0]["text"]
    assert first_instructions == RESEARCH_PROMPT + "\nReturn only JSON matching the response schema, with no Markdown or commentary."
    answer_instructions = auth.calls[1]["input"][0]["content"][0]["text"]
    assert answer_instructions == ANSWER_PROMPT + "\nWhen finished, return only JSON matching the response schema, with no Markdown or commentary."
    outputs = [item for item in auth.calls[-1]["input"] if item.get("type") == "function_call_output"]
    assert [(item["call_id"], json.loads(item["output"])) for item in outputs] == [
        ("calc_a", {"value": "120"}), ("calc_b", {"value": "30"})]
    assert any(item.get("encrypted_content") == ENCRYPTED for item in auth.calls[-1]["input"])
    assert ENCRYPTED not in json.dumps(result.trace)
    assert ENCRYPTED not in json.dumps([asdict(item) for item in reported])
    assert reported[-1].input_tokens is None and reported[-1].output_tokens is None
    assert result.trace[-1]["budget"]["semantic_attempts"] == 2


def test_plan_selected_source_completion_citations_session_reopen_without_localization(tmp_path):
    model, auth = plan_model(
        Reply("research", decision()),
        Reply("research", decision(requests=[request("read", query="", target="E1", mode="full")])),
        Reply("research", decision("answer", ["E2"])),
        Reply("answer", answer("Seven units under sheltered conditions. [E2]"), empty_terminal=True),

    )
    store = SQLiteSessionStore(tmp_path / "plan-session.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search,
                                     fetch=lambda _url, **_kwargs: FetchedMaterial(URL, FULL_TEXT),
                                     lexical_search=forbidden)
    result = session.ask("What quantity does the standard specify and under which condition?")
    assert result.answer == "Seven units under sheltered conditions. [1]"
    assert [item.id for item in result.selected_evidence] == ["E2", "E1"]
    answer_packet = packet(auth.calls[3])
    assert [item["id"] for item in answer_packet["evidence"]] == ["E2", "E1"]
    assert [item["content"] for item in answer_packet["evidence"]] == [FULL_TEXT, HIGHLIGHT]
    assert len(result.citation_uses) == 1 and not result.citation_uses[0].support
    assert result.citations[0].materials == result.selected_evidence
    reopened = ResearchSession.open(session.session_id, store=store, model=model,
                                    search=forbidden, fetch=forbidden, lexical_search=forbidden)
    assert reopened.turns == session.turns and reopened.acquisitions == session.acquisitions
    assert [p["text"]["format"]["name"] for p in auth.calls] == [
        "research", "research", "research", "answer"]
    assert auth.calls[-1]["model"] == "gpt-6.1-sol" and auth.calls[-1]["reasoning"] == {"effort": "medium"}


@pytest.mark.parametrize("reply", [Reply("answer", answer(), interrupted=True),
                                   Reply("answer", answer(), status="incomplete")])
def test_plan_uncompleted_answer_cannot_commit_session(tmp_path, reply):
    model, _ = plan_model(Reply("research", decision()), Reply("research", decision("answer", ["E1"])), reply)
    store = SQLiteSessionStore(tmp_path / "failed-session.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search,
                                     fetch=forbidden, lexical_search=forbidden)
    with pytest.raises(RunError):
        session.ask("What quantity applies?")
    assert session.turns == session.acquisitions == ()
    assert ResearchSession.open(session.session_id, store=store).turns == ()


def test_plan_undeclared_function_namespace_never_executes_calculator():
    model, _ = plan_model(Reply("answer", tool="1 + 1", namespace="unapproved"))
    calculated = []
    with pytest.raises(ModelError):
        model("answer", ANSWER_PROMPT, {}, {}, calculator=lambda expression: calculated.append(expression))
    assert calculated == []


@pytest.mark.parametrize("mutation", ["unclosed_delta", "omitted_item", "completed_error", "terminal_sequence"])
def test_plan_conflicting_or_unverified_completion_never_becomes_authoritative(mutation):
    class InvalidCompletion:
        def stream(self, payload):
            first = {"id": "first", "type": "message", "role": "assistant", "phase": "final_answer",
                     "status": "completed", "content": [{"type": "output_text", "text": "{}"}]}
            terminal = {"model": payload["model"], "status": "completed", "output": []}
            if mutation == "unclosed_delta":
                events = [{"type": "response.output_text.delta", "output_index": 0,
                           "content_index": 0, "item_id": "first", "delta": "{}"}]
            else:
                events = [{"type": "response.output_item.done", "output_index": 0, "item": first}]
                if mutation == "omitted_item":
                    events.append({"type": "response.output_item.done", "output_index": 1,
                                   "item": {**first, "id": "second"}})
                    terminal["output"] = [first]
                elif mutation == "completed_error":
                    terminal["output"] = [first]
                    terminal["error"] = {"code": "untrusted"}
                else:
                    events[0]["sequence_number"] = 2
                    terminal["output"] = [first]
            events.append({"type": "response.completed", "response": terminal})
            if mutation == "terminal_sequence":
                events[-1]["sequence_number"] = 1
            return Stream(events)
    model, auth = plan_model(InvalidCompletion())
    with pytest.raises(ModelError):
        model("research", RESEARCH_PROMPT, {}, {})
    assert len(auth.calls) == 1 and auth.streams[0].closed


def test_api_default_retains_cap_and_request_contract_without_plan_auth(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-api-value")
    calls = []
    def post(url, **kwargs):
        calls.append((url, copy.deepcopy(kwargs)))
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "status": "completed", "output": [{"type": "message", "content": [
                {"type": "output_text", "text": "{}"}]}], "usage": usage()})
    model = OpenAIModel(built_in_model_config(), post=post)
    assert model("research", "Unchanged API instructions.", {"question": "Synthetic"}, {}) == "{}"
    assert len(calls) == 1
    body = calls[0][1]["json"]
    assert body["max_output_tokens"] == 12000 and body["service_tier"] == "fast"
    assert body["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert "stream" not in body and "tools" not in body
    assert calls[0][1]["headers"]["Authorization"] == "Bearer synthetic-api-value"
