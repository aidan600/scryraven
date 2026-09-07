"""Offline scenarios through the actual application, with only external calls faked."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from core.linkup_transport import DiscoveryCandidate, FetchedMaterial, LinkupTransportError
from scryraven import __main__ as cli
from scryraven import research
from scryraven.model import ModelError
from scryraven.research import RunError, RunLimits, run

QUESTION = "What is the maximum allowed weight?"
URL = "https://example.test/rules"


class Model:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, stage, _prompt, material, _schema):
        self.calls.append((stage, material))
        expected_stage, reply = self.replies.pop(0)
        assert stage == expected_stage
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply)


def search_for(query="official rules"):
    return "research", {"action": "search", "query": query, "candidate_refs": []}


def read(*refs):
    return "research", {"action": "read", "query": "", "candidate_refs": list(refs)}


def done():
    return "research", {"action": "done", "query": "", "candidate_refs": []}


def analysis(decision="supported", refs=("E1",), *, next_need=None, active=None):
    return "analyst", {
        "decision": decision,
        "findings": [{"text": "Maximum weight is 16 pounds.", "support_refs": list(refs)}] if refs else [],
        "active_evidence_refs": list(refs) if active is None else active,
        "explanation": "The acquired rule establishes the limit." if decision == "supported" else "The limit is unresolved.",
        "next_need": next_need,
    }


def author(text="The maximum weight is 16 pounds. [[E1]]"):
    return "author", {"answer": text}


def discover(_query):
    return [DiscoveryCandidate("Official rules", URL, "DISCOVERY-ONLY: 99 pounds")]


def fetch(url):
    return FetchedMaterial(url, "Rule: The weight shall not exceed 16 pounds.")


def test_supported_flow_preserves_fetched_evidence_and_selects_author_material():
    unused_url = "https://example.test/history"
    fetched = {
        unused_url: "Historical background without the requested limit.",
        URL: "Rule: The weight shall not exceed 16 pounds.",
    }
    model = Model(search_for(), read("C1", "C2"), analysis(refs=("E2",), active=["E1", "E2"]), author("16 pounds. [[E2]]"))
    result = run(QUESTION, model=model, search=lambda q: [
        DiscoveryCandidate("Background", unused_url, "DISCOVERY-ONLY: 99 pounds"),
        discover(q)[0],
    ], fetch=lambda url: FetchedMaterial(url, fetched[url]))

    assert result.posture == "supported"
    assert result.answer == f"16 pounds. [Official rules]({URL})"
    analyst_input = next(material for stage, material in model.calls if stage == "analyst")
    author_input = next(material for stage, material in model.calls if stage == "author")
    assert [item["content"] for item in analyst_input["evidence"]] == list(fetched.values())
    assert author_input["evidence"] == [analyst_input["evidence"][1]]
    assert author_input["evidence"][0]["id"] == result.evidence[1].id
    assert "DISCOVERY-ONLY" not in json.dumps([analyst_input, author_input])
    assert unused_url not in json.dumps(author_input)
    assert "attempts" not in author_input and "candidates" not in author_input
    with pytest.raises(FrozenInstanceError):
        result.evidence[1].content = "replacement"
    assert result.trace[-1]["posture"] == "supported"


def test_analyst_semantic_need_returns_to_research_and_expands_same_collection():
    gap = "Whether the weight limit applies to this type of ball."
    second_url = "https://example.test/clarification"
    queries = []

    def search(query):
        queries.append(query)
        return discover(query) if len(queries) == 1 else [DiscoveryCandidate("Clarification", second_url, "A navigation clue")]

    model = Model(
        search_for("initial query"), read("C1"), analysis("research_needed", refs=(), next_need=gap, active=["E1"]),
        search_for("Research chose this new query"), read("C1"), analysis(refs=("E2",), active=["E1", "E2"]),
        author("16 pounds. [[E2]]"),
    )
    result = run(QUESTION, model=model, search=search, fetch=fetch)
    analyses = [material for stage, material in model.calls if stage == "analyst"]
    second_research = model.calls[3][1]
    assert second_research["question"] == QUESTION
    assert second_research["need"] == gap
    assert queries == ["initial query", "Research chose this new query"]
    assert analyses[0]["evidence"] == analyses[1]["evidence"][:1]
    assert [item.id for item in result.evidence] == ["E1", "E2"]
    assert result.evidence[1].url == second_url
    assert any(event.get("next_need") == gap for event in result.trace)
    assert result.posture == "supported"


def test_research_revises_poor_discovery_and_failed_reads_before_analyst():
    queries = []
    reads = []

    def search(query):
        queries.append(query)
        if len(queries) == 1:
            return []
        return discover(query) if len(queries) == 2 else [DiscoveryCandidate("Working rules", URL + "2", "clue")]

    def read_source(url):
        reads.append(url)
        if len(reads) == 1:
            raise LinkupTransportError("raw provider detail must not escape")
        return fetch(url)

    model = Model(search_for("weak query"), search_for("better query"), read("C1"), search_for("alternative"), read("C2"), analysis(), author())
    result = run(QUESTION, model=model, search=search, fetch=read_source)
    assert len(queries) > 1 and reads == [URL, URL + "2"]
    assert len(result.evidence) == 1 and result.evidence[0].url == URL + "2"
    assert any(event["action"] == "read_failed" for event in result.trace)
    assert "raw provider detail" not in json.dumps(result.trace)
    assert result.posture == "supported"


@pytest.mark.parametrize("failure", ["empty_discovery", "discovery_error", "failed_fetch", "empty_fetch"])
def test_discovery_or_failed_read_cannot_support_answer(failure):
    steps = [search_for()]
    if failure in {"failed_fetch", "empty_fetch"}:
        steps.append(read("C1"))
    steps.extend([done(), analysis("unable", refs=()), author("The available research in this run did not establish the weight limit.")])
    model = Model(*steps)

    def search(query):
        if failure == "discovery_error":
            raise LinkupTransportError("private raw response")
        return [] if failure == "empty_discovery" else discover(query)

    def read_source(url):
        if failure == "empty_fetch":
            return FetchedMaterial(url, "")
        raise LinkupTransportError("private raw response")

    result = run(QUESTION, model=model, search=search, fetch=read_source)
    assert result.posture == "unable" and result.stop_reason == "not_established"
    assert result.evidence == ()
    assert "this run did not establish" in result.answer
    assert "99" not in result.answer
    for stage, material in model.calls:
        if stage in {"analyst", "author"}:
            assert material["evidence"] == []
            assert "DISCOVERY-ONLY" not in json.dumps(material)
    assert "private raw" not in json.dumps(result.trace)


def test_operational_bound_preserves_unresolved_analysis_in_author_handoff():
    gap = "The applicable maximum weight."
    model = Model(search_for(), analysis("research_needed", refs=(), next_need=gap), author("The available research in this run did not establish the limit."))
    result = run(QUESTION, model=model, search=discover, fetch=fetch, limits=RunLimits(research_passes=1, navigation_steps=1))
    assert result.analysis.decision == "research_needed"
    assert result.posture == "unable" and result.stop_reason == "research_bound"
    author_input = model.calls[-1][1]
    assert author_input["posture"] == "unable"
    assert author_input["unresolved_need"] == gap
    assert author_input["stop_reason"] == "research_bound"
    assert any(event["action"] == "navigation_bound" for event in result.trace)


def test_malformed_output_can_be_repaired_without_exposing_values_and_adjacent_citations_resolve():
    model = Model(
        search_for(), read("C1", "C2"), ("analyst", {"decision": "private rejected value"}),
        analysis(refs=("E1", "E2")), author("16 pounds. [[E1]] [[E2]]"),
    )
    result = run(QUESTION, model=model, search=lambda q: [
        *discover(q), DiscoveryCandidate("Second rules", URL + "2", "clue"),
    ], fetch=fetch)
    assert result.posture == "supported"
    assert f"[Official rules]({URL})" in result.answer
    assert f"[Second rules]({URL}2)" in result.answer
    rejected = next(event for event in result.trace if event["action"] == "response_rejected")
    assert rejected["stage"] == "analyst" and rejected["issues"]
    assert "private rejected value" not in json.dumps(result.trace)
    assert "private rejected value" not in json.dumps(model.calls)


@pytest.mark.parametrize("kind,stage,code", [
    ("support", "analyst", "invalid_evidence_reference"),
    ("active", "analyst", "invalid_evidence_reference"),
    ("citation", "citations", "invalid_citation_reference"),
    ("unselected", "citations", "invalid_citation_reference"),
    ("missing", "citations", "missing_citation"),
    ("raw_link", "citations", "unresolved_author_link"),
    ("malformed", "analyst", "malformed_model_response"),
    ("model", "analyst", "model_transport_failed"),
    ("author", "author", "model_transport_failed"),
])
def test_invalid_references_and_model_failures_are_clear_and_stage_local(kind, stage, code):
    verdict = analysis(refs=("E404",)) if kind == "support" else analysis()
    if kind == "active":
        verdict = analysis(active=["E404"])
    if kind == "malformed":
        verdict = "analyst", {"decision": "banana", "private": "raw model output"}
    if kind == "model":
        verdict = "analyst", ModelError("model_transport_failed")
    output = {
        "citation": "16 pounds. [[E404]]", "unselected": "16 pounds. [[E2]]",
        "missing": "16 pounds.", "raw_link": "16 pounds. [invented](https://not-acquired.test)",
    }.get(kind, "16 pounds. [[E1]]")
    final = ("author", ModelError("model_transport_failed")) if kind == "author" else author(output)
    model = Model(search_for(), read("C1", "C2"), verdict, *([verdict] if kind == "malformed" else []), final)
    with pytest.raises(RunError) as captured:
        run(QUESTION, model=model, search=lambda q: [*discover(q), DiscoveryCandidate("Other", URL + "2", "clue")], fetch=fetch)
    error = captured.value
    assert (error.stage, error.code) == (stage, code)
    assert error.trace[-1] == {"stage": stage, "action": "failed", "code": code}
    assert "raw model output" not in str(error) + json.dumps(error.trace)


def test_cli_invokes_real_application_and_real_linkup_adapters(monkeypatch, capsys):
    from core import linkup_transport

    calls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    def post(url, **kwargs):
        calls.append((url, kwargs["json"]))
        if url == linkup_transport.LINKUP_SEARCH_URL:
            return Response({"results": [{"url": URL, "name": "Rules", "content": "DISCOVERY-ONLY"}]})
        assert url == linkup_transport.LINKUP_FETCH_URL
        return Response({"markdown": "The limit is 16 pounds."})

    model = Model(search_for(), read("C1"), analysis(), author())
    monkeypatch.setenv("LINKUP_API_KEY", "offline-test-value")
    monkeypatch.setattr(linkup_transport.requests, "post", post)
    monkeypatch.setattr(research, "OpenAIModel", lambda: model)
    assert cli.main([QUESTION, "--trace"]) == 0
    captured = capsys.readouterr()
    assert f"[Rules]({URL})" in captured.out
    assert calls[1][1] == {"url": URL}
    assert json.loads(captured.err)["trace"][-1]["posture"] == "supported"

    monkeypatch.setattr(research, "OpenAIModel", lambda: Model(("research", ModelError("model_configuration_missing"))))
    assert cli.main([QUESTION, "--trace"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "research: model_configuration_missing" in captured.err
    assert "Traceback" not in captured.err
