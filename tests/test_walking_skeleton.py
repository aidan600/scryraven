"""Offline scenarios through the actual application, with only external calls faked."""

from __future__ import annotations

import json

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
        if isinstance(reply, str):
            return reply
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
    analyst_input["evidence"][1]["content"] = "replacement in the Analyst input"
    author_input["evidence"][0]["content"] = "replacement in the Author input"
    assert result.evidence[1].content == fetched[URL]
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


@pytest.mark.parametrize("failure", ["empty_discovery", "discovery_error", "failed_fetch", "empty_fetch", "wrong_source", "unhelpful_material"])
def test_discovery_or_failed_read_cannot_support_answer(failure):
    steps = [search_for()]
    if failure not in {"empty_discovery", "discovery_error"}:
        steps.append(read("C1"))
    if failure != "unhelpful_material":
        steps.append(done())
    steps.extend([analysis("unable", refs=()), author("The available research in this run did not establish the weight limit.")])
    model = Model(*steps)

    def search(query):
        if failure == "discovery_error":
            raise LinkupTransportError("private raw response")
        return [] if failure == "empty_discovery" else discover(query)

    def read_source(url):
        if failure == "empty_fetch":
            return FetchedMaterial(url, "")
        if failure == "wrong_source":
            return FetchedMaterial(url + "other", "A rule from a different source.")
        if failure == "unhelpful_material":
            return FetchedMaterial(url, "This page describes a different game without a weight limit.")
        raise LinkupTransportError("private raw response")

    result = run(QUESTION, model=model, search=search, fetch=read_source)
    assert result.posture == "unable" and result.stop_reason == "not_established"
    assert bool(result.evidence) == (failure == "unhelpful_material")
    assert "this run did not establish" in result.answer
    assert "99" not in result.answer
    for stage, material in model.calls:
        if stage in {"analyst", "author"}:
            if stage == "author" or failure != "unhelpful_material":
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


def test_malformed_output_can_be_repaired_without_exposing_values():
    model = Model(
        search_for(), read("C1"), ("analyst", {"decision": "private rejected value"}),
        analysis(), ("author", '```json\n{"answer":"16 pounds. [E1]"}\n```'),
    )
    result = run(QUESTION, model=model, search=discover, fetch=fetch)
    assert result.posture == "supported"
    assert f"[Official rules]({URL})" in result.answer
    rejected = next(event for event in result.trace if event["action"] == "response_rejected")
    assert rejected["stage"] == "analyst" and rejected["issues"]
    assert "private rejected value" not in json.dumps(result.trace)


def test_json_syntax_repair_has_safe_location_diagnostics():
    model = Model(
        ("research", '{"action":"search" "query":"private bad value","candidate_refs":[]}'),
        search_for(), read("C1"), analysis(), author(),
    )
    result = run(QUESTION, model=model, search=discover, fetch=fetch)
    rejected = next(event for event in result.trace if event["action"] == "response_rejected")
    assert any(issue["type"] == "expected_comma" for issue in rejected["issues"])
    assert "private bad value" not in json.dumps(result.trace)
    assert result.posture == "supported"


def test_citation_grammar_preserves_prose_and_renders_only_selected_acquired_sources():
    sources = [DiscoveryCandidate(f"Rules {index} [edition]", URL + str(index), "clue") for index in range(1, 13)]
    links = {index: f"[Rules {index} \\[edition\\]]({URL}{index})" for index in (1, 2, 12)}
    cases = [
        ("[E1] [E12]", links[1] + " " + links[12]),
        ("[[E1]][[E2]]", links[1] + links[2]),
        ("[E1, E2]", links[1] + " " + links[2]),
        ("[[E1, E2]]", links[1] + " " + links[2]),
        ("[[E1], [E2]]", links[1] + " " + links[2]),
        ("[ E1,\n E2 ]", links[1] + " " + links[2]),
        ("[E1] again [E1]", links[1] + " again " + links[1]),
        ("[note] [context] [[ordinary prose]]", "[note] [context] [[ordinary prose]]"),
        ("**[E1]**, ([E12]);\n[E2] (a qualification).", f"**{links[1]}**, ({links[12]});\n{links[2]} (a qualification)."),
    ]
    model = Model(
        search_for(), read(*(f"C{index}" for index in range(1, 13))),
        analysis(refs=("E1", "E2", "E12")), author("\n".join(draft for draft, _ in cases)),
    )
    result = run(QUESTION, model=model, search=lambda query: sources, fetch=fetch)
    assert result.posture == "supported"
    assert result.answer == "\n".join(expected for _, expected in cases)
    resolved = next(event for event in result.trace if event["action"] == "resolved")
    assert resolved["evidence_ids"] == ["E1", "E12", "E2"]


@pytest.mark.parametrize("marker,code,pattern", [
    ("[E999]", "invalid_citation_reference", "unknown_or_unselected_alias"),
    ("[E2]", "invalid_citation_reference", "unknown_or_unselected_alias"),
    ("[[E1], [E999]]", "invalid_citation_reference", "unknown_or_unselected_alias"),
    ("[[E1, E999]]", "invalid_citation_reference", "unknown_or_unselected_alias"),
    ("[E]", "malformed_citation_reference", "incomplete_alias"),
    ("[E1", "malformed_citation_reference", "incomplete_alias"),
    ("E1]", "malformed_citation_reference", "incomplete_alias"),
    ("[e1]", "malformed_citation_reference", "incomplete_alias"),
    ("[[E1]", "malformed_citation_reference", "unbalanced_brackets"),
    ("[[E1]]]", "malformed_citation_reference", "unbalanced_brackets"),
    (r"\[E1]", "malformed_citation_reference", "escaped_citation"),
    ("`[E1]`", "malformed_citation_reference", "literal_citation"),
    ("\n```\n[E1]", "malformed_citation_reference", "literal_citation"),
    ("\n~~~\n[E1]\n~~~", "malformed_citation_reference", "literal_citation"),
    ("![E1]", "unresolved_author_link", "author_link_or_image"),
    ("[invented](https://not-acquired.test)", "unresolved_author_link", "author_link_or_image"),
    ("\n[other]: /unacquired", "unresolved_author_link", "author_link_or_image"),
])
def test_bad_citations_fail_even_beside_a_valid_alias_without_exposing_the_draft(marker, code, pattern):
    model = Model(search_for(), read("C1", "C2"), analysis(), author("Private rejected answer. [E1] " + marker))
    with pytest.raises(RunError) as captured:
        run(QUESTION, model=model, search=lambda q: [*discover(q), DiscoveryCandidate("Unselected", URL + "2", "clue")], fetch=fetch)
    error = captured.value
    assert (error.stage, error.code) == ("citations", code)
    rejected = next(event for event in error.trace if event["action"] == "rejected")
    assert rejected["pattern"] == pattern and rejected["offset"] is not None
    assert rejected["selected_evidence_ids"] == ["E1"]
    if "E999" in marker:
        assert "E999" in rejected["evidence_ids"]
    assert "Private rejected answer" not in json.dumps(error.trace)
    assert "not-acquired.test" not in json.dumps(error.trace)


@pytest.mark.parametrize("kind,stage,code", [
    ("support", "analyst", "invalid_evidence_reference"),
    ("active", "analyst", "invalid_evidence_reference"),
    ("missing", "citations", "missing_citation"),
])
def test_invalid_analysis_references_and_missing_citations_are_stage_local(kind, stage, code):
    verdict = analysis(refs=("E404",)) if kind == "support" else analysis()
    if kind == "active":
        verdict = analysis(active=["E404"])
    model = Model(search_for(), read("C1"), verdict, author("16 pounds."))
    with pytest.raises(RunError) as captured:
        run(QUESTION, model=model, search=discover, fetch=fetch)
    error = captured.value
    assert (error.stage, error.code) == (stage, code)
    assert error.trace[-1]["stage"] == stage and error.trace[-1]["action"] == "failed"


@pytest.mark.parametrize("stage", ["research", "analyst", "author"])
@pytest.mark.parametrize("failure", ["transport", "malformed"])
def test_model_failures_stop_at_the_responsibility_without_raw_output(stage, failure):
    model = Model(search_for(), read("C1"), analysis(), author())

    def fail_at_stage(current, *args):
        if current == stage:
            if failure == "transport":
                raise ModelError("model_transport_failed")
            return '{"private":"raw model output"}'
        return model(current, *args)

    with pytest.raises(RunError) as captured:
        run(QUESTION, model=fail_at_stage, search=discover, fetch=fetch)
    error = captured.value
    assert error.stage == stage
    assert error.code == ("model_transport_failed" if failure == "transport" else "malformed_model_response")
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
    assert cli.main([QUESTION, "--trace", "--trace-evidence"]) == 0
    captured = capsys.readouterr()
    assert f"[Rules]({URL})" in captured.out
    assert calls[1][1] == {"url": URL}
    diagnostics = json.loads(captured.err)
    assert diagnostics["trace"][-1]["posture"] == "supported"
    assert diagnostics["selected_evidence"] == [{
        "id": "E1", "url": URL, "title": "Rules", "content": "The limit is 16 pounds.",
    }]
    assert "DISCOVERY-ONLY" not in captured.err

    monkeypatch.setattr(research, "OpenAIModel", lambda: Model(("research", ModelError("model_configuration_missing"))))
    assert cli.main([QUESTION, "--trace"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "research: model_configuration_missing" in captured.err
    assert "Traceback" not in captured.err
