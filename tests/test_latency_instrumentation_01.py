"""Body-free per-call timing and usage through the ordinary Research path."""

import json

from test_research_loop import Script, answer, decision, no_fetch, request

from core.exa_transport import DiscoveryCandidate
from scryraven.model import ModelConfig, OpenAIModel
from scryraven.research import RunLimits, run


def test_same_route_request_indexes_and_durations_use_the_injected_clock():
    now = [0.0]

    def search(query):
        now[0] += {"first": 2.0, "second": 3.0}[query]
        return [DiscoveryCandidate(query, f"https://example.org/{query}",
                                   f"The {query} exact source text.",
                                   context_kind="provider_highlights")]

    model = Script(
        decision(requests=[request(query="first"), request(query="second")]),
        decision("answer"),
        answer("The available material does not establish the requested conclusion.", "unable"),
    )
    result = run("What can be established?", model=model, search=search, fetch=no_fetch,
                 clock=lambda: now[0])

    operations = [event for event in result.trace if event["action"] == "acquisition_timing"]
    assert [(item["route_index"], item["request_index"], item["provider"], item["external"],
             item["started_elapsed_seconds"], item["ended_elapsed_seconds"], item["duration_seconds"])
            for item in operations] == [
                (1, 1, "exa", True, 0.0, 2.0, 2.0),
                (1, 2, "exa", True, 2.0, 5.0, 3.0),
            ]
    assert sum(item["duration_seconds"] for item in operations) - max(
        item["duration_seconds"] for item in operations) == 2.0
    assert all("query" not in item and "source" not in item and "url" not in item
               for item in operations)


def test_bound_before_provider_io_is_not_counted_as_external_execution():
    model = Script(decision(), answer("Research could not complete.", "unable"))
    result = run("What can be established?", model=model,
                 search=lambda _: (_ for _ in ()).throw(AssertionError("provider called")),
                 fetch=no_fetch, limits=RunLimits(semantic_attempts=2, external_attempts=0))

    assert not any(event["action"] == "acquisition_timing" for event in result.trace)
    assert result.trace[-1]["budget"]["external_attempts"] == 0


def test_existing_model_usage_boundary_populates_safe_call_record(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    def post(_url, **kwargs):
        stage = kwargs["json"]["text"]["format"]["name"]
        output = decision("answer") if stage == "research" else answer(
            "No source establishes the conclusion.", "unable")
        usage = ({"input_tokens": 100, "input_tokens_details": {
            "cached_tokens": 20, "cache_write_tokens": 10,
        }, "output_tokens": 50, "output_tokens_details": {"reasoning_tokens": 30}}
                 if stage == "research" else {})
        return Response({"status": "completed", "usage": usage, "output": [{
            "type": "message", "phase": "final_answer", "content": [{
                "type": "output_text", "text": json.dumps(output),
            }],
        }]})

    model = OpenAIModel(ModelConfig(), post=post)
    result = run("What follows?", model=model, search=lambda _: [], fetch=no_fetch)
    starts = [event for event in result.trace if event["action"] == "model_started"]
    returned = [event for event in result.trace if event["action"] == "model_returned"]

    assert [(item["contract"], item["model"], item["reasoning_effort"])
            for item in starts] == [
                ("research", "gpt-6-luna", "high"),
                ("answer", "gpt-6-sol", "medium"),
            ]
    assert {key: returned[0]["usage"][key] for key in (
        "input_tokens", "cached_input_tokens", "cache_write_tokens",
        "ordinary_uncached_tokens", "output_tokens", "reasoning_tokens",
    )} == {
        "input_tokens": 100, "cached_input_tokens": 20, "cache_write_tokens": 10,
        "ordinary_uncached_tokens": 70, "output_tokens": 50, "reasoning_tokens": 30,
    }
    assert all(returned[1]["usage"][key] is None for key in (
        "input_tokens", "cached_input_tokens", "cache_write_tokens",
        "ordinary_uncached_tokens", "output_tokens", "reasoning_tokens",
    ))
    assert all(item["duration_seconds"] >= 0 for item in returned)
