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


def orient(question=QUESTION, needs=None):
    return "research", {"answer_needs": needs or [{
        "need": question, "authority": "Responsible governing body", "material_sought": "Current official rule",
        "temporal_requirement": "Applicable governing rule, regardless of publication age",
    }], "focus": question}


def search_for(query="official rules", *, revised=None, summary="Locate the responsible governing rule.", hypothesis=None):
    return "research", {"action": "search", "query": query, "candidate_refs": [],
                        "revised_answer_needs": revised, "summary": summary,
                        "search_hypothesis": hypothesis or {
                            "evidence_target": "Governing rule text", "novelty": "Initial governing publication route",
                            "expected_value": "Establish the applicable limit", "acquirability": "Public federation rulebook",
                            "third_search_reason": None,
                        }}


def read(*refs, summary="Read the direct rule rather than the adjacent summary."):
    return "research", {"action": "read", "query": "", "candidate_refs": list(refs),
                        "revised_answer_needs": None, "summary": summary, "search_hypothesis": None}


def done():
    return "research", {"action": "done", "query": "", "candidate_refs": [],
                        "revised_answer_needs": None, "summary": "No useful unread navigation remains.", "search_hypothesis": None}


def relevance(*refs, summary="Retain material relevant to the question."):
    return "research", {"relevant_evidence_refs": list(refs), "summary": summary}


def analysis(decision="supported", refs=("E1",), *, next_need=None, active=None, need_ref="N1", new_reason=None):
    return "analyst", {
        "decision": decision,
        "coverage": [{"need": QUESTION, "status": "supported" if refs else "unresolved",
                      "findings": [{"text": "Maximum weight is 16 pounds.", "support_refs": list(refs)}] if refs else [],
                      "limitation": "" if refs else "The applicable maximum is unresolved."}],
        "active_evidence_refs": list(refs) if active is None else active,
        "explanation": "The acquired rule establishes the limit." if decision == "supported" else "The limit is unresolved.",
        "next_need": next_need,
        "next_need_ref": need_ref if next_need else None, "new_need_reason": new_reason,
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
    model = Model(orient(), search_for(), read("C1", "C2"), relevance("E1", "E2"),
                  analysis(refs=("E2",), active=["E1", "E2"]), author("16 pounds. [[E2]]"))
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
        if len(queries) == 1:
            return [DiscoveryCandidate("Weak lead", URL + "-weak", "clue"), *discover(query)]
        return [DiscoveryCandidate("Clarification", second_url, "A navigation clue")]

    model = Model(
        orient(), search_for("initial query"), read("C2"), relevance("E1"),
        analysis("research_needed", refs=(), next_need=gap, active=["E1"]),
        search_for("Research chose this new query"), read("C999"), read("C3"), relevance("E2"),
        analysis(refs=("E2",), active=["E1", "E2"]),
        author("16 pounds. [[E2]]"),
    )
    result = run(QUESTION, model=model, search=search, fetch=fetch)
    analyses = [material for stage, material in model.calls if stage == "analyst"]
    second_research = next(material for stage, material in model.calls if stage == "research" and material.get("need") == gap)
    assert second_research["question"] == QUESTION
    assert second_research["need"] == gap
    assert queries == ["initial query", "Research chose this new query"]
    assert analyses[0]["evidence"] == analyses[1]["evidence"][:1]
    assert [item.id for item in result.evidence] == ["E1", "E2"]
    assert result.evidence[1].url == second_url
    rejected = next(event for event in result.trace if event["action"] == "selection_rejected")
    assert rejected["cause"] == "unknown_alias"
    assert rejected["valid_candidate_refs"] == ["C1", "C2", "C3"]  # Stable aliases across the whole run.
    assert rejected["evidence_count"] == 1
    assert any(event.get("next_need") == gap for event in result.trace)
    assert result.posture == "supported"


@pytest.mark.parametrize("refs,cause", [
    (("C999",), "unknown_alias"),
    (("[C2]",), "malformed_alias"),
    (("private malformed selection",), "malformed_alias"),
    ((), "empty_selection"),
    (("C1", "C999"), "unknown_alias"),
])
def test_research_corrects_invalid_selection_before_any_fetch(refs, cause):
    reads = []
    chosen_url = URL + "-chosen"
    sources = [*discover("query"), DiscoveryCandidate("Chosen rules", chosen_url, "DISCOVERY-ONLY")]

    def read_source(url):
        reads.append(url)
        return fetch(url)

    model = Model(orient(), search_for(), read(*refs), read("C2"), relevance("E1"), analysis(), author())
    result = run(QUESTION, model=model, search=lambda query: sources, fetch=read_source)
    assert reads == [chosen_url]  # Neither guesses nor valid fragments of a rejected selection are fetched.
    assert [(item.id, item.url) for item in result.evidence] == [("E1", chosen_url)]
    correction = next(material for stage, material in model.calls if "selection_correction" in material)
    assert correction["question"] == QUESTION and correction["need"] == QUESTION
    assert correction["acquired_sources"] == []
    assert correction["selection_correction"]["valid_candidate_refs"] == [item["id"] for item in correction["candidates"]]
    rejected = next(event for event in result.trace if event["action"] == "selection_rejected")
    assert rejected["stage"] == "research" and rejected["cause"] == cause
    assert rejected["evidence_count"] == 0
    assert "private malformed selection" not in json.dumps(result.trace)
    downstream = [material for stage, material in model.calls if stage in {"analyst", "author"}]
    assert "DISCOVERY-ONLY" not in json.dumps(downstream)
    assert all(material["evidence"][0]["content"] == fetch(chosen_url).readable_text for material in downstream)
    assert result.posture == "supported"


def test_repeated_invalid_selection_stops_without_fetch_or_downstream_evidence():
    def invalid_research(stage, _prompt, material, _schema):
        assert stage == "research"
        if material["phase"] == "orientation":
            return json.dumps(orient()[1])
        return json.dumps(read("C1", "C999")[1] if material["candidates"] else search_for()[1])

    with pytest.raises(RunError) as captured:
        run(QUESTION, model=invalid_research, search=discover, fetch=lambda url: pytest.fail("Rejected selection reached Fetch"))
    error = captured.value
    assert (error.stage, error.code) == ("research", "invalid_candidate_reference")
    rejections = [event for event in error.trace if event["action"] == "selection_rejected"]
    assert len(rejections) > 1
    assert all(event["cause"] == "unknown_alias" and event["evidence_count"] == 0 for event in rejections)
    assert error.trace[-1]["action"] == "failed"


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

    alternative = {**search_for()[1]["search_hypothesis"],
                   "novelty": "Another publication surface after the rulebook Fetch failed",
                   "third_search_reason": "The discovered federation handbook links to a public HTML edition."}
    model = Model(orient(), search_for("weak query"), search_for("better query"), read("C1"),
                  search_for("alternative", hypothesis=alternative), read("C2"), relevance("E1"), analysis(), author())
    result = run(QUESTION, model=model, search=search, fetch=read_source)
    assert len(queries) > 1 and reads == [URL, URL + "2"]
    assert len(result.evidence) == 1 and result.evidence[0].url == URL + "2"
    assert any(event["action"] == "read_failed" for event in result.trace)
    assert "raw provider detail" not in json.dumps(result.trace)
    assert result.posture == "supported"


@pytest.mark.parametrize("failure", ["empty_discovery", "discovery_error", "failed_fetch", "empty_fetch", "wrong_source", "unhelpful_material"])
def test_discovery_or_failed_read_cannot_support_answer(failure):
    steps = [orient(), search_for()]
    if failure not in {"empty_discovery", "discovery_error"}:
        steps.append(read("C1"))
    if failure != "unhelpful_material":
        steps.append(done())
    else:
        steps.append(relevance())
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
            assert material["evidence"] == []
            assert "DISCOVERY-ONLY" not in json.dumps(material)
    assert "private raw" not in json.dumps(result.trace)


def test_operational_bound_preserves_unresolved_analysis_in_author_handoff():
    gap = "The applicable maximum weight."
    model = Model(orient(), search_for(), analysis("research_needed", refs=(), next_need=gap),
                  author("The available research in this run did not establish the limit."))
    result = run(QUESTION, model=model, search=discover, fetch=fetch, limits=RunLimits(research_passes=1, navigation_steps=1))
    assert result.analysis.decision == "research_needed"
    assert result.posture == "unable" and result.stop_reason == "research_bound"
    author_input = model.calls[-1][1]
    assert author_input["posture"] == "unable"
    assert author_input["unresolved_need"] == gap
    assert author_input["stop_reason"] == "research_bound"
    assert any(event["action"] == "navigation_bound" for event in result.trace)


def test_second_hypothesis_receives_actual_yield_without_a_quality_gate():
    revised = {
        "evidence_target": "Maintained federation handbook",
        "novelty": "The announcement archive exposed only background; try the maintained rules reference",
        "expected_value": "Find the operative limit rather than its announcement",
        "acquirability": "A public HTML handbook is linked from the federation navigation",
        "third_search_reason": None,
    }
    queries = []

    def search(query):
        queries.append(query)
        old = DiscoveryCandidate("Archive", URL + "-archive", "DISCOVERY-ONLY")
        return [old] if len(queries) == 1 else [old, old, DiscoveryCandidate("Invalid", "not-a-url", "clue"), *discover(query)]

    model = Model(orient(), search_for("announcement archive"), search_for("maintained handbook", hypothesis=revised),
                  read("C2"), relevance("E1"), analysis(), author())
    result = run(QUESTION, model=model, search=search, fetch=fetch)
    navigation = [material for _, material in model.calls if material.get("phase") == "navigation"]
    assert navigation[1]["attempts"][0]["new_candidate_refs"] == ["C1"]
    outcome = navigation[2]["attempts"][-1]
    assert (outcome["returned"], outcome["new_candidate_count"], outcome["duplicate_url_count"]) == (4, 1, 2)
    assert outcome["new_candidate_refs"] == ["C2"] and outcome["search_hypothesis"] == revised
    assert navigation[2]["discovery_allowance"] == {"need_ref": "N1", "searches_used": 2, "remaining": 1}
    assert len(queries) == 2 and result.posture == "supported"


def exceptional_search():
    return search_for("named rules supplement", hypothesis={
        "evidence_target": "Named rules supplement", "novelty": "Separate supplement beyond the handbook and archive",
        "expected_value": "Resolve the exception missing from both prior routes",
        "acquirability": "Public supplement identified by the federation's handbook listing",
        "third_search_reason": "The second discovery explicitly names the supplement and its publisher.",
    })


def test_fuse_blocks_fourth_and_paraphrase_but_preserves_candidates_reads_and_partial_support():
    queries, reads = [], []

    def search(query):
        queries.append(query)
        return [*discover(query), DiscoveryCandidate("Supplement", URL + "/supplement", "DISCOVERY-ONLY")]

    def acquire(url):
        reads.append(url)
        return fetch(url)

    gap = "The maximum permitted mass under the applicable rules."
    model = Model(
        orient(), search_for("first route"), search_for("second route"), exceptional_search(),
        search_for("fourth wording", revised=NEEDS), read("C1"), relevance("E1"),
        analysis("research_needed", next_need=gap),
        search_for("fifth wording after paraphrase"), read("C2"), relevance("E1", "E2"),
        analysis("unable", refs=("E1", "E2")),
        author("The acquired text gives 16 pounds. [E1, E2] This run did not resolve applicability."),
    )
    result = run(QUESTION, model=model, search=search, fetch=acquire)
    assert len(queries) == 3 and reads == [URL, URL + "/supplement"]
    discoveries = [event for event in result.trace if event["action"] == "discovery_started"]
    assert [event["attempt"] for event in discoveries] == [1, 2, 3]
    assert discoveries[-1]["search_hypothesis"]["third_search_reason"]
    blocked = [event for event in result.trace if event["action"] == "discovery_fuse_reached"]
    assert len(blocked) == 2 and all(event["need_ref"] == "N1" and event["remaining"] == 0 for event in blocked)
    followup = next(material for _, material in model.calls if material.get("phase") == "navigation" and material["need"] == gap)
    assert followup["discovery_allowance"]["searches_used"] == 3
    assert len(followup["candidates"]) == 2 and len([a for a in followup["attempts"] if "query" in a]) == 3
    assert result.posture == "partial" and [item.id for item in result.evidence] == ["E1", "E2"]
    assert [item["id"] for item in model.calls[-1][1]["evidence"]] == ["E1", "E2"]
    assert "DISCOVERY-ONLY" not in json.dumps([m for stage, m in model.calls if stage in {"analyst", "author"}])


def test_new_analyst_gap_has_own_allowance_and_returning_to_old_need_keeps_its_count():
    queries = []

    def search(query):
        queries.append(query)
        return [DiscoveryCandidate("Rule", URL + str(len(queries)), "clue")]

    model = Model(
        orient(), search_for("rule"), search_for("handbook"), exceptional_search(), read("C1"), relevance("E1"),
        analysis("research_needed", next_need="Why the earlier edition used a different limit.", need_ref=None,
                 new_reason="The first investigation concerned the operative limit; the historical reason has not been investigated."),
        search_for("edition change explanation"), read("C4"), relevance("E1", "E2"),
        analysis("research_needed", next_need="The operative maximum weight, restated.", need_ref="N1"),
        search_for("another current limit wording"), done(), relevance("E1", "E2"),
        analysis("unable", refs=("E1", "E2")), author("The acquired limit is 16 pounds. [E1] Some applicability remains unresolved."),
    )
    result = run(QUESTION, model=model, search=search, fetch=fetch)
    assert len(queries) == 4
    starts = [event for event in result.trace if event["action"] == "discovery_started"]
    assert [(e["need_ref"], e["attempt"]) for e in starts] == [("N1", 1), ("N1", 2), ("N1", 3), ("N2", 1)]
    blocked = next(e for e in result.trace if e["action"] == "discovery_fuse_reached")
    assert blocked["need_ref"] == "N1" and blocked["searches_used"] == 3
    analyses = [material for stage, material in model.calls if stage == "analyst"]
    assert [(n["ref"], n["searches"]) for n in analyses[-1]["research_needs"]] == [("N1", 3), ("N2", 1)]
    assert len(analyses[-1]["discovery_history"]) == 4 and result.posture == "partial"


def test_third_search_without_concrete_case_can_read_without_spending_another_call():
    queries = []

    def search(query):
        queries.append(query)
        return discover(query)

    model = Model(orient(), search_for("first"), search_for("second"), search_for("unjustified third"),
                  read("C1"), relevance("E1"), analysis(), author())
    result = run(QUESTION, model=model, search=search, fetch=fetch)
    assert queries == ["first", "second"] and result.posture == "supported"
    rejection = next(event for event in result.trace if event["action"] == "search_rejected")
    assert rejection["missing_fields"] == ["third_search_reason"] and rejection["remaining"] == 1


def test_failed_discovery_spends_fuse_and_repeated_block_returns_honest_limitation():
    queries = []

    def search(query):
        queries.append(query)
        raise LinkupTransportError("private provider detail")

    model = Model(orient(), search_for("first"), search_for("second"), exceptional_search(),
                  search_for("fourth"), search_for("fifth"), analysis("unable", refs=()),
                  author("This run could not establish the limit."))
    result = run(QUESTION, model=model, search=search, fetch=fetch, limits=RunLimits(navigation_steps=20))
    assert len(queries) == 3 and not result.evidence and result.posture == "unable"
    assert "private provider detail" not in json.dumps(result.trace)
    assert len([e for e in result.trace if e["action"] == "discovery_failed"]) == 3


@pytest.mark.parametrize("need_ref,new_reason,code", [
    ("N999", None, "invalid_research_need_reference"),
    (None, " ", "new_research_need_unexplained"),
    ("N1", "Treat this as new", "invalid_research_need_reference"),
])
def test_invalid_handoff_cannot_silently_mint_a_fresh_allowance(need_ref, new_reason, code):
    model = Model(orient(), search_for(), read("C1"), relevance("E1"),
                  analysis("research_needed", next_need="Restated limit", need_ref=need_ref, new_reason=new_reason))
    with pytest.raises(RunError, match=code):
        run(QUESTION, model=model, search=discover, fetch=fetch)


def test_malformed_output_can_be_repaired_without_exposing_values():
    model = Model(
        orient(), search_for(), read("C1"), relevance("E1"), ("analyst", {"decision": "private rejected value"}),
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
        orient(),
        ("research", '{"action":"search" "query":"private bad value","candidate_refs":[]}'),
        search_for(), read("C1"), relevance("E1"), analysis(), author(),
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
        orient(), search_for(), read(*(f"C{index}" for index in range(1, 13))), relevance("E1", "E2", "E12"),
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
    model = Model(orient(), search_for(), read("C1", "C2"), relevance("E1"),
                  analysis(), author("Private rejected answer. [E1] " + marker))
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
    model = Model(orient(), search_for(), read("C1"), relevance("E1"), verdict, author("16 pounds."))
    with pytest.raises(RunError) as captured:
        run(QUESTION, model=model, search=discover, fetch=fetch)
    error = captured.value
    assert (error.stage, error.code) == (stage, code)
    assert error.trace[-1]["stage"] == stage and error.trace[-1]["action"] == "failed"


@pytest.mark.parametrize("stage", ["research", "analyst", "author"])
@pytest.mark.parametrize("failure", ["transport", "malformed"])
def test_model_failures_stop_at_the_responsibility_without_raw_output(stage, failure):
    model = Model(orient(), search_for(), read("C1"), relevance("E1"), analysis(), author())

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

    model = Model(orient(), search_for(), read("C1"), relevance("E1"), analysis(), author())
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


MULTI_QUESTION = "Under Meadow Games rules, what is the equipment limit, excess-equipment penalty, and replacement condition?"
NEEDS = [{
    "need": need, "authority": "Meadow Games federation", "material_sought": material,
    "temporal_requirement": "Applicable current edition, not necessarily the newest page",
} for need, material in [
    ("Equipment limit", "Current equipment rule"),
    ("Excess-equipment penalty", "Current competition penalty rule"),
    ("Replacement condition", "Current replacement rule and exceptions"),
]]
RULES_TEXT = "A player may carry four items. Carrying extra items incurs a two-point penalty."
REPLACEMENT_TEXT = "Damaged equipment may be replaced after the referee approves."


def component_analysis(last_ref="E1", *, decision=None, qualified=False):
    texts = ["The limit is four items.", "The penalty is two points.", "Replacement requires referee approval."]
    coverage = [{
        "need": item["need"], "status": "qualified" if qualified else "supported",
        "findings": [{"text": text, "support_refs": ["E1" if index < 2 else last_ref]}],
        "limitation": "Based on the readable federation handbook summary." if qualified else "",
    } for index, (item, text) in enumerate(zip(NEEDS, texts, strict=True))]
    if last_ref is None:
        coverage[-1].update(status="unresolved", findings=[], limitation="Replacement conditions were not established.")
    return "analyst", {
        "decision": decision or ("supported" if last_ref else "research_needed"),
        "coverage": coverage, "active_evidence_refs": [],
        "explanation": "The combined passages establish the findings; the coverage identifies any remaining gap.",
        "next_need": "The rule establishing when damaged equipment may be replaced." if last_ref is None else None,
        "next_need_ref": "N1" if last_ref is None else None, "new_need_reason": None,
    }


@pytest.mark.parametrize("separate_source", [False, True])
def test_multi_component_authority_orientation_combination_and_pipeline_triage(separate_source):
    """Scripted model judgments exercise the real handoffs, not live semantic quality."""
    replacement_url = "https://equipment.test/replacement"
    irrelevant_url = "https://meadow.test/rules-archive"
    needs = [dict(item) for item in NEEDS]
    if separate_source:
        needs[-1]["authority"] = "Meadow equipment committee"
    model = Model(
        orient(MULTI_QUESTION, needs), search_for("Meadow federation current competition equipment rules"),
        read("C2", "C2", "C3", *(["C4"] if separate_source else []),
             summary="The summary points to C2, the responsible rule owner; C1 adds no direct evidence."),
        relevance("E1", *(["E3"] if separate_source else []), summary="The archive is unrelated boilerplate."),
        component_analysis("E3" if separate_source else "E1"),
        author("The limit is four items and the penalty is two points. [E1] "
               + f"Damaged equipment requires referee approval for replacement. [{'E3' if separate_source else 'E1'}]"),
    )
    queries, reads = [], []

    def search(query):
        # Research's semantic orientation really precedes discovery and reaches navigation.
        assert model.calls[0][1]["phase"] == "orientation"
        assert model.calls[-1][1]["answer_needs"] == needs
        queries.append(query)
        return [
            DiscoveryCandidate("A secondary explainer", "https://summary.test/game", "DISCOVERY-ONLY: federation owns rules"),
            DiscoveryCandidate("Federation equipment rules", URL, "DISCOVERY-ONLY"),
            DiscoveryCandidate("Archived rules", irrelevant_url, "Possibly useful"),
            DiscoveryCandidate("Equipment committee rule", replacement_url, "DISCOVERY-ONLY"),
        ]

    def acquire(url):
        reads.append(url)
        content = {
            URL: RULES_TEXT + (" " + REPLACEMENT_TEXT if not separate_source else ""),
            irrelevant_url: "UNRELATED BODY: website cookie policy and navigation.",
            replacement_url: REPLACEMENT_TEXT,
        }[url]
        return FetchedMaterial(url, content)

    result = run(MULTI_QUESTION, model=model, search=search, fetch=acquire)
    assert result.posture == "supported" and not model.replies
    assert len(queries) == 1  # No mechanical search-per-component or duplicate reads.
    assert reads == [URL, irrelevant_url, *([replacement_url] if separate_source else [])]
    assert result.evidence[1].content.startswith("UNRELATED BODY")  # Retained, not destroyed.
    downstream = [material for stage, material in model.calls if stage in {"analyst", "author"}]
    assert "UNRELATED BODY" not in json.dumps(downstream)
    assert "DISCOVERY-ONLY" not in json.dumps(downstream)
    assert all([item["id"] for item in material["evidence"]] == ["E1", *(["E3"] if separate_source else [])]
               for material in downstream)
    assert len(downstream[-1]["coverage"]) == 3
    assert all(item["findings"] for item in downstream[-1]["coverage"])
    assert [event["action"] for event in result.trace].index("oriented") < [event["action"] for event in result.trace].index("discovery_started")
    assert "UNRELATED BODY" not in json.dumps(result.trace)


@pytest.mark.parametrize("resolve_gap", [False, True])
def test_missing_component_drives_focused_research_preserving_supported_parts_at_bound(resolve_gap):
    gap = component_analysis(None)[1]["next_need"]
    new_url = URL + "/replacement"
    queries, reads = [], []

    def search(query):
        queries.append(query)
        return [DiscoveryCandidate("Federation rules", URL, "clue"), DiscoveryCandidate("Replacement rule", new_url, "clue")]

    def acquire(url):
        reads.append(url)
        return FetchedMaterial(url, RULES_TEXT if url == URL else (
            REPLACEMENT_TEXT if resolve_gap else "Unrelated product warranty."
        ))

    final = component_analysis("E2" if resolve_gap else None)
    model = Model(
        orient(MULTI_QUESTION, NEEDS), search_for(), read("C1"), relevance("E1"), component_analysis(None),
        search_for("Federation replacement condition"), read("C1", "C2"),
        relevance(*(["E2"] if resolve_gap else [])), final,
        author("The limit is four items, with a two-point penalty for extras. [E1] " + (
            "Replacement requires referee approval. [E2]" if resolve_gap else
            "This run did not establish the conditions for replacing damaged equipment."
        )),
    )
    result = run(MULTI_QUESTION, model=model, search=search, fetch=acquire, limits=RunLimits(research_passes=2))
    assert reads == [URL, new_url]  # Existing E1 is not acquired again on the second selection.
    analyses = [material for stage, material in model.calls if stage == "analyst"]
    assert analyses[0]["evidence"][0] == analyses[1]["evidence"][0]
    assert analyses[1]["previous_analysis"]["coverage"][:2] == component_analysis(None)[1]["coverage"][:2]
    followup = [material for stage, material in model.calls if material.get("phase") == "navigation" and material["need"] == gap]
    assert followup and all(material["question"] == MULTI_QUESTION for material in followup)
    assert len(queries) == 2 and result.analysis.coverage[:2] == research.Analysis.model_validate(final[1]).coverage[:2]
    assert result.posture == ("supported" if resolve_gap else "partial")
    author_input = model.calls[-1][1]
    assert author_input["coverage"] == final[1]["coverage"]
    if not resolve_gap:
        assert result.stop_reason == "research_bound"
        assert author_input["posture"] == "partial" and author_input["unresolved_need"] == gap
        assert [item["id"] for item in author_input["evidence"]] == ["E1"]
        assert "did not establish" in result.answer and f"]({URL})" in result.answer


def test_secondary_fallback_revisable_needs_and_restoring_omitted_acquisition_without_refetch():
    wrong_needs = [{**NEEDS[0], "need": "Buying equipment"}]
    sources = [
        DiscoveryCandidate("Official rulebook", URL + "/primary", "clue"),
        DiscoveryCandidate("Federation handbook summary", URL, "clue"),
        DiscoveryCandidate("Equipment committee clarification", URL + "/replacement", "clue"),
    ]
    reads = []

    def acquire(url):
        reads.append(url)
        if url == sources[0].url:
            raise LinkupTransportError("primary unavailable")
        return FetchedMaterial(url, RULES_TEXT if url == URL else REPLACEMENT_TEXT)

    revised_done = {**done()[1], "revised_answer_needs": NEEDS}
    model = Model(
        orient(MULTI_QUESTION, wrong_needs), search_for(), read("C1", "C2", "C3"), relevance("E1"),
        component_analysis(None, qualified=True), ("research", revised_done), relevance("E1", "E2"),
        component_analysis("E2", qualified=True),
        author("The readable handbook gives a four-item limit and two-point penalty. [E1] "
               "Replacement requires referee approval. [E2] The main rulebook was unavailable in this run."),
    )
    result = run(MULTI_QUESTION, model=model, search=lambda query: sources, fetch=acquire)
    assert result.posture == "supported"
    assert reads == [item.url for item in sources]
    analyses = [material for stage, material in model.calls if stage == "analyst"]
    assert analyses[0]["answer_needs"] == wrong_needs
    assert analyses[1]["answer_needs"] == NEEDS  # Analyst corrected the original hypothesis.
    assert [item["id"] for item in analyses[0]["evidence"]] == ["E1"]
    assert [item["id"] for item in analyses[1]["evidence"]] == ["E1", "E2"]
    selections = [material for stage, material in model.calls if material.get("phase") == "relevance"]
    assert selections[1]["new_evidence"] == []  # Restored from run-local identity, not another source request.
    assert [item["id"] for item in selections[1]["available_sources"]] == ["E1", "E2"]
    assert all(item.status == "qualified" for item in result.analysis.coverage)
    assert any(event["action"] == "orientation_revised" for event in result.trace)


@pytest.mark.parametrize("failure", ["unknown_relevance", "withheld_support", "premature_supported"])
def test_selections_and_component_completeness_fail_mechanically_in_the_actual_flow(failure):
    selected = relevance("E404") if failure == "unknown_relevance" else relevance("E1")
    verdict = component_analysis("E2") if failure == "withheld_support" else component_analysis(None, decision="supported")
    model = Model(orient(MULTI_QUESTION, NEEDS), search_for(), read("C1", "C2"), selected, verdict)
    with pytest.raises(RunError) as captured:
        run(MULTI_QUESTION, model=model, search=lambda query: [*discover(query),
            DiscoveryCandidate("Withheld source", URL + "2", "clue")], fetch=fetch)
    error = captured.value
    assert error.stage == ("research" if failure == "unknown_relevance" else "analyst")
    assert error.code == ("supported_with_unresolved_component" if failure == "premature_supported" else "invalid_evidence_reference")
    assert all(stage != "author" for stage, material in model.calls)


@pytest.mark.parametrize("temporal_target", ["applicable", "named_period", "latest_event"])
def test_temporal_orientation_selects_applicable_material_instead_of_newest_page(temporal_target):
    question = {
        "applicable": "What are the currently applicable Meadow Games equipment rules?",
        "named_period": "What equipment rules applied in the Meadow Games opening season?",
        "latest_event": "What is the most recently announced Meadow Games equipment change?",
    }[temporal_target]
    temporal_basis = {
        "applicable": "Present governing edition; an older publication can remain in force.",
        "named_period": "Opening-season edition, even if a later edition superseded it afterward.",
        "latest_event": "The latest announcement by event time; recency matters to this question.",
    }[temporal_target]
    needs = [{**NEEDS[0], "need": question, "temporal_requirement": temporal_basis}]
    sources = [
        DiscoveryCandidate("Fresh secondary commentary", "https://commentary.test/new", "Published today; DISCOVERY-ONLY"),
        DiscoveryCandidate("Federation opening-season rules", URL + "/opening", "Original official edition"),
        DiscoveryCandidate("Federation governing rules", URL + "/governing", "Published months ago; currently governing"),
        DiscoveryCandidate("Federation latest announcement", URL + "/announcement", "Most recent announcement"),
    ]
    target_index = {"applicable": 2, "named_period": 1, "latest_event": 3}[temporal_target]
    statement = {
        "applicable": "This edition remains in force and supersedes the opening-season edition. Limit: four items.",
        "named_period": "During the opening season the limit was five items. Later seasons use another edition.",
        "latest_event": "The latest federation announcement introduces a six-item limit for next season, not this season.",
    }[temporal_target]
    verdict = analysis()[1]
    verdict["coverage"] = [{"need": question, "status": "supported", "limitation": "",
                            "findings": [{"text": statement, "support_refs": ["E1"]}]}]
    model = Model(orient(question, needs), search_for(), read(f"C{target_index + 1}", summary=temporal_basis),
                  relevance("E1", summary=temporal_basis), ("analyst", verdict), author(statement + " [E1]"))
    fetched = []

    def acquire(url):
        fetched.append(url)
        return FetchedMaterial(url, statement)

    result = run(question, model=model, search=lambda query: sources, fetch=acquire)
    assert fetched == [sources[target_index].url] and result.posture == "supported"
    for stage, material in model.calls:
        if material.get("phase") in {"navigation", "relevance"} or stage == "analyst":
            assert material["answer_needs"][0]["temporal_requirement"] == temporal_basis
    orientation = next(event for event in result.trace if event["action"] == "oriented")
    assert orientation["answer_needs"][0]["temporal_requirement"] == temporal_basis
    author_input = model.calls[-1][1]
    assert author_input["evidence"][0]["content"] == statement
    assert "DISCOVERY-ONLY" not in json.dumps(author_input)
