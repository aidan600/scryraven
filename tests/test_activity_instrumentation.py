"""Observe the ordinary executor using controlled transport and model calls."""

import json
from threading import Barrier

import pytest
import requests
from test_dual_read_acquisition import TEXT, dual_result
from test_image_inputs import answer as image_answer
from test_image_inputs import decision as image_decision
from test_image_inputs import reply, scripted, session_image
from test_research_loop import Script, answer, decision, no_fetch, request

from core import exa_transport, serper_transport
from core.exa_transport import DiscoveryCandidate
from scryraven import research


@pytest.mark.parametrize("transport, env, kind, payload_key", [
    (exa_transport, "EXA_API_KEY", "search", "query"),
    (serper_transport, "SERPER_API_KEY", "search_lexical", "q"),
])
@pytest.mark.parametrize("configured", [False, True])
def test_only_actual_search_dispatch_supplies_query_text(monkeypatch, transport, env, kind, payload_key, configured):
    monkeypatch.delenv(env, raising=False)
    if configured:
        monkeypatch.setenv(env, "offline-test-value")
    events = []
    calls = []

    def reject(_url, *, json, **_kwargs):
        calls.append(json[payload_key])
        assert events[-1]["action"] == "search_dispatched"
        assert events[-1]["query"] == json[payload_key]
        raise requests.HTTPError()

    monkeypatch.setattr(transport, "post_provider_request", reject)
    model = Script(decision(requests=[request(kind, query="  exact question wording  ")]),
                   decision("return"), answer("Could not establish it.", "unable"))
    result = research.run("What is the threshold?", model=model, fetch=no_fetch, activity=events.append)
    acquisition = [event for event in events if event["action"] == "acquisition_finished"]
    assert [event["status"] for event in acquisition] == ["error" if configured else "unavailable"]
    assert calls == (["exact question wording"] if configured else [])
    assert sum("query" in event for event in events) == int(configured)
    assert not {event["action"] for event in events} & {event["action"] for event in result.trace}


def test_parallel_search_dispatch_and_admission_share_one_group():
    events = []
    both_dispatched = Barrier(2, timeout=2)

    def search(query):
        both_dispatched.wait()
        assert {event["query"] for event in events if event["action"] == "search_dispatched"} == {"first", "second"}
        return [DiscoveryCandidate("Example", "https://example.test/sample", TEXT,
                                   context_kind="provider_highlights")]

    model = Script(decision(requests=[request(query="first"), request(query="second")]),
                   decision("return", ["E1"]), answer("The threshold is seven. [E1]"))
    result = research.run("What is the threshold?", model=model, search=search, fetch=no_fetch, activity=events.append)
    batch = [event for event in events if event.get("group_index") == 1]
    assert [event["action"] for event in batch] == [
        "search_batch_started", "search_dispatched", "search_dispatched",
        "acquisition_finished", "acquisition_finished", "search_batch_finished",
    ]
    assert [event["request_index"] for event in batch[3:5]] == [1, 2]
    assert [(event["candidate_count"], event["new_candidate_count"], event["highlight_count"])
            for event in batch[3:5]] == [(1, 1, 1), (1, 0, 1)]
    assert len(result.evidence) == 1


def test_dual_read_and_retained_read_are_distinct_logical_operations(monkeypatch):
    events = []
    url = "https://example.test/original?private_parameter=sentinel"
    monkeypatch.setattr(research, "configured_read_providers", lambda: ("linkup", "exa"))

    def retrieve(target, *, providers, timeout_seconds):
        assert target == url and timeout_seconds > 0
        assert events[-1]["action"] == "acquisition_started" and events[-1]["external"]
        return dual_result(target, providers)

    monkeypatch.setattr(research, "fetch_dual", retrieve)
    model = Script(decision(requests=[request("read", target=url, mode="full"),
                                      request("read", target=url, mode="local")]),
                   decision("return", ["E1"]), answer("The threshold is seven. [E1]"))
    result = research.run(f"Read {url}", model=model, activity=events.append)
    operations = [event for event in events if event.get("kind") == "read"]
    assert [(event["action"], event["request_index"], event["external"]) for event in operations] == [
        ("acquisition_started", 1, True), ("acquisition_finished", 1, True),
        ("acquisition_started", 2, False), ("acquisition_finished", 2, False),
    ]
    assert operations[1]["original_text_retrieved"] and operations[1]["read_providers"] == ("linkup", "exa")
    assert operations[3]["material_count"] == 1 and not operations[3]["original_text_retrieved"]
    assert all(event["hostname"] == "example.test" for event in operations)
    assert all(value not in json.dumps(events) for value in (TEXT, "private_parameter"))
    assert result.citations[0].url == url


def test_answer_validation_resumes_composition_for_correction_and_activity_failure_is_nonfatal():
    events = []

    def broken_activity(event):
        events.append(event["action"])
        raise OSError("isolated activity failure")

    model = Script(decision("return"), answer("The claim is unsupported."),
                   answer("Could not establish the claim.", "unable"))
    result = research.run("What is the threshold?", model=model, fetch=no_fetch, activity=broken_activity)
    assert events[:4] == ["answer_dispatch_started", "answer_validation_started",
                          "answer_dispatch_started", "answer_validation_started"]
    assert [call[0] for call in model.calls] == ["research", "answer", "answer"]
    assert result.posture == "unable"


def test_retained_image_inspection_counts_as_material_without_exposing_the_image(monkeypatch):
    read = request("read", target="I1", mode="local")
    tool = {"status": "completed", "output": [{
        "type": "function_call", "name": "library_read", "call_id": "inspect-image",
        "arguments": json.dumps({"target": "I1", "focus": "", "start_char": None, "end_char": None}),
    }]}
    model, payloads = scripted(monkeypatch, [reply(image_decision([read])), reply(image_decision()),
                                           tool, reply(image_answer())])
    events = []
    result = research._run_turn("Describe my earlier image", model=model, images=(session_image(),),
                                activity=events.append)
    inspections = [event for event in events if event["action"] in {
        "acquisition_finished", "answer_inspection_finished",
    }]
    assert [(event["kind"], event["status"], event["material_count"]) for event in inspections] == [
        ("read", "ok", 1), ("read", "ok", 1),
    ]
    assert len(payloads) == 4 and result.image_ids == ("I1",)
    assert "unsafe.png" not in json.dumps(events)


def test_exhausted_budget_never_announces_a_search_or_retrieval_start():
    url = "https://example.test/missing"
    model = Script(decision(requests=[request(query="first"), request("read", target=url)]),
                   decision("return"), answer("Could not establish the claim.", "unable"))
    events = []

    def unexpected_dispatch(_):
        pytest.fail("dispatched an acquisition with no budget")

    research.run(f"Read {url}", model=model, search=unexpected_dispatch, fetch=unexpected_dispatch,
                 limits=research.RunLimits(external_attempts=0), activity=events.append)
    relevant = [event for event in events if event.get("kind") in {"search", "read"}]
    assert [(event["action"], event["kind"], event["status"]) for event in relevant] == [
        ("acquisition_finished", "search", "unavailable"),
        ("acquisition_finished", "read", "unavailable"),
    ]
