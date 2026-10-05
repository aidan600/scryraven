"""The fresh-turn bootstrap changes provider effort, never evidence authority."""

import json
from threading import Lock

import pytest
from test_exa_transport import Response
from test_research_loop import Script, answer, decision, request

from core import exa_transport as exa
from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.research import run
from scryraven.sources import Evidence


def test_deep_request_keeps_exact_highlights_and_excludes_generated_fields():
    calls = []
    passages = ["  First source selection.\n", "Second source selection."]

    def post(url, **kwargs):
        calls.append(kwargs)
        return Response({
            "results": [{"url": "https://example.test/source", "title": "Source",
                         "highlights": passages, "summary": "GENERATED", "text": "UNREQUESTED",
                         "reasoning": "GENERATED", "confidence": "high"}],
            "output": {"content": "GENERATED", "grounding": [{"confidence": "high"}]},
            "answer": "GENERATED", "summary": "GENERATED",
        })

    candidate = exa.search_exa("Evidence objective", search_type="deep", api_key="offline", post=post)[0]
    assert calls[0]["json"] == {
        "query": "Evidence objective", "type": "deep", "numResults": 6,
        "contents": {"text": False, "highlights": {
            "query": "Evidence objective", "dynamic": True, "verbosity": "high"}},
    }
    assert calls[0]["headers"]["Exa-Beta"] == exa.EXA_DYNAMIC_HIGHLIGHTS_BETA
    assert candidate.context == "\n\n[Separate provider highlight; intervening context omitted]\n\n".join(passages)
    assert candidate.url == "https://example.test/source"
    assert candidate.context_kind == "provider_highlights"
    assert "GENERATED" not in candidate.context and "UNREQUESTED" not in candidate.context


@pytest.mark.parametrize("search_type", ["deep-reasoning", "deep-max", "Auto", "", None, [], True])
def test_only_auto_and_deep_are_accepted_before_io(search_type):
    with pytest.raises(ValueError, match="search_type must be auto or deep"):
        exa.search_exa("Objective", search_type=search_type, post=lambda *a, **k: pytest.fail("I/O"))


def production_post(monkeypatch, calls, *, fail_first=False):
    monkeypatch.setenv(exa.EXA_API_KEY_ENV, "offline-test-value")
    gate = Lock()

    def post(url, **kwargs):
        assert url == exa.EXA_SEARCH_URL
        with gate:
            calls.append(kwargs)
            failed = fail_first and len(calls) == 1
        if failed:
            raise OSError("Unexposed provider failure")
        return Response({"results": [{"url": "https://example.test/fact",
                                      "highlights": ["The stated value is seven."]}]})

    monkeypatch.setattr(exa.requests, "post", post)


def test_one_shot_across_same_and_later_routes_with_safe_mode_telemetry(monkeypatch):
    calls, observed = [], []
    production_post(monkeypatch, calls)
    diagnostics = TurnDiagnostics()

    def observe(event):
        observed.append(event)
        diagnostics.observe(event)

    model = Script(decision(requests=[request(query="first"), request(query="second")]),
                   decision(requests=[request(query="third")]), decision("answer", ["E1"]), answer())
    result = run("Value?", model=model, observe=observe)
    assert sorted((call["json"]["query"], call["json"]["type"]) for call in calls[:2]) == [
        ("first", "deep"), ("second", "auto"),
    ]
    assert (calls[2]["json"]["query"], calls[2]["json"]["type"]) == ("third", "auto")
    timings = [event for event in observed if event["action"] == "acquisition_timing"]
    assert [event["provider_search_type"] for event in timings] == ["deep", "auto", "auto"]
    assert [row["provider_search_type"] for row in diagnostics.acquisitions] == ["deep", "auto", "auto"]
    assert all("query" not in event and "url" not in event for event in timings)
    assert result.selected_evidence[0].content == "The stated value is seven."
    assert all("provider_search_type" not in json.dumps(packet) for _, _, packet, _ in model.calls)


@pytest.mark.parametrize(("turn", "retained"), [
    (2, ()), (1, (Evidence("E1", "https://example.test/prior", "Prior", "Retained."),)),
])
def test_followup_or_retained_entry_uses_auto(monkeypatch, turn, retained):
    calls = []
    production_post(monkeypatch, calls)
    model = Script(decision(), decision("answer"), answer("No established result.", "unable"))
    run("Value?", model=model, session_turn=turn, retained_acquisitions=retained)
    assert [call["json"]["type"] for call in calls] == ["auto"]


def test_other_operations_do_not_consume_bootstrap(monkeypatch):
    calls, lexical, reads = [], [], []
    production_post(monkeypatch, calls)

    def lexical_search(query):
        lexical.append(query)
        return [DiscoveryCandidate("Navigation", "https://example.test/page", "Snippet")]

    def fetch(url):
        reads.append(url)
        return FetchedMaterial(url, "Read source text.")

    model = Script(decision(requests=[request("search_lexical", "lexical"),
                                     request("read", target="C1"), request("find", "source")]),
                   decision(), decision("answer"), answer("Not established.", "unable"))
    result = run("Value?", model=model, lexical_search=lexical_search, fetch=fetch)
    assert lexical == ["lexical"] and reads == ["https://example.test/page"]
    assert [call["json"]["type"] for call in calls] == ["deep"]
    operations = [e for e in result.trace if e["action"] == "acquisition_timing"]
    assert [e["provider"] for e in operations] == ["serper", "linkup", "local", "exa"]
    assert all("provider_search_type" not in e for e in operations[:3])


def test_no_generic_search_means_no_deep_request(monkeypatch):
    calls = []
    production_post(monkeypatch, calls)
    model = Script(decision("answer"), answer("Not established.", "unable"))
    run("Value?", model=model)
    assert not calls


def test_executed_failure_consumes_bootstrap(monkeypatch):
    calls = []
    production_post(monkeypatch, calls, fail_first=True)
    model = Script(decision(), decision(), decision("answer", ["E1"]), answer())
    result = run("Value?", model=model)
    assert [call["json"]["type"] for call in calls] == ["deep", "auto"]
    assert result.posture == "supported"


def test_new_run_gets_its_own_bootstrap(monkeypatch):
    calls = []
    production_post(monkeypatch, calls)
    for _ in range(2):
        run("Value?", model=Script(decision(), decision("answer", ["E1"]), answer()))
    assert [call["json"]["type"] for call in calls] == ["deep", "deep"]


def test_diagnostics_drops_unrecognized_provider_mode():
    diagnostics = TurnDiagnostics()
    diagnostics.observe({"stage": "research", "action": "acquisition_timing", "kind": "search", "provider": "exa",
                         "provider_search_type": "Private query must not be telemetry"})
    assert "provider_search_type" not in diagnostics.acquisitions[0]
