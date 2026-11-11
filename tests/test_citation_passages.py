"""Passage location and durable custody through the ordinary Answer path."""

import json
from hashlib import sha256

import pytest
from test_research_first_resumable import initial, reply, request, scripted, stages
from test_research_loop import Script, answer, decision, no_fetch, search

from core.exa_transport import DiscoveryCandidate
from scryraven.results import resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence, exact_view, support_text


def locator(ref, occurrence, text):
    return {"ref": ref, "occurrence": occurrence, "text": text}


def test_same_opinion_occurrences_save_distinct_original_text_with_independent_fallback(tmp_path):
    majority = "Majority. The approval was subject to review."
    dissent = "Dissent. The approval was\n  final upon filing."
    body = f"Opinion of the court\n\n{majority}\n\nSeparate opinion\n\n{dissent}"

    def discover(query):
        return [DiscoveryCandidate("Example v. City", "https://example.org/opinion", body,
                                   context_kind="provider_highlights")]

    draft = ("The majority treated the approval as reviewable. [E1] "
             "The dissent considered it final upon filing. [E1] See the case for its procedural history. [E1]")
    model = Script(decision(), decision("return", ["E1"]), {
        **answer(draft),
        "citation_passages": [
            locator("E1", 1, majority),
            locator("E1", 2, "Dissent. The approval was final upon filing."),
            locator("E1", 3, "This wording was not acquired."),
        ],
    })
    store = SQLiteSessionStore(tmp_path / "legal-citations.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=discover, fetch=no_fetch)
    result = session.ask("Where did the majority and dissent differ on finality?")
    assert [call[0] for call in model.calls] == ["research", "research", "answer"]
    assert result.answer == draft.replace("[E1]", "[1]")
    assert all("citation_passages" not in event.get("decision", {}) for event in result.trace)

    reopened = ResearchSession.open(session.session_id, store=SQLiteSessionStore(store.path))
    saved, = reopened.turns
    assert saved == session.turns[0]
    assert saved.citation_uses == result.citation_uses
    material, = saved.citations[0].materials
    first, second, fallback = saved.citation_uses
    assert not fallback.support
    assert [(use.number, saved.answer[use.start:use.end]) for use in (first, second, fallback)] == [(1, "[1]")] * 3
    for use, expected in ((first, majority), (second, dissent)):
        region, = use.support
        assert region.start_char == body.index(expected)
        assert region.material_sha256 == sha256(body.encode()).hexdigest()
        assert region.passage_sha256 == sha256(expected.encode()).hexdigest()
        assert support_text(region, material) == expected


def test_passage_matching_stays_with_the_cited_selected_version_and_view():
    first = Evidence("E1", "https://example.org/code", "Statute", "(2)(B) This provision applies. Old wording.")
    second = Evidence("E2", first.url, first.title, "(3) This provision applies. New wording.", source_id="E1")
    view = exact_view(second, 0, 27)
    result, citations, uses = resolve_citations(
        "§ 10(2)(B) [E1]. § 10(3) [E2@0:27]. Old wording [E2@0:27]. New wording [E2@0:27].",
        [first, view], [first, second], [],
        passages=[locator("E1", 1, "(2)(B) This provision applies."),
                  locator(view.id, 1, "(3) This provision applies."),
                  locator(view.id, 2, "Old wording."),
                  locator(view.id, 3, "New wording.")],
    )
    assert result == "§ 10(2)(B) [1]. § 10(3) [1]. Old wording [1]. New wording [1]."
    assert citations[0].materials == (first, view)
    assert support_text(uses[0].support[0], first) == "(2)(B) This provision applies."
    assert support_text(uses[1].support[0], view) == "(3) This provision applies."
    assert uses[2].support == uses[3].support == ()


def test_source_alias_without_exact_selection_and_coalesced_references_cannot_grant_passage():
    first = Evidence("E1", "https://example.org/opinion", "Opinion", "First holding. Later sentence.")
    a, b = exact_view(first, 0, 14), exact_view(first, 15, len(first.content))
    _, _, uses = resolve_citations(
        f"Canonical alias [E1]. Coalesced [{a.id},{b.id}]. Exact [{b.id}].",
        [a, b], [first], [],
        passages=[locator("E1", 1, "First holding."),
                  locator(a.id, 1, "First holding."),
                  locator(b.id, 1, "Later sentence."),
                  locator(b.id, 2, "Later sentence.")],
    )
    assert uses[0].support == uses[1].support == ()
    assert support_text(uses[2].support[0], b) == "Later sentence."


@pytest.mark.parametrize("proposals", [
    None,
    [locator("E1", 1, "Repeated wording.")],
    [locator("E1", 1, "Repeated\nwording.")],
    [locator("E1", 1, "Different wording.")],
    [locator("E1", 2, "One unique sentence.")],
    [locator("E2", 1, "One unique sentence.")],
    [locator("E1", 1, "One unique sentence."), locator("E1", 1, "Different wording.")],
])
def test_unavailable_or_ambiguous_passage_preserves_the_source_citation(proposals):
    source = Evidence("E1", "https://example.org/opinion", "Opinion",
                      "Repeated wording. One unique sentence. Repeated wording.")
    text, citations, uses = resolve_citations("Supported fact [E1].", [source], [source], [], passages=proposals)
    assert text == "Supported fact [1]."
    assert citations[0].materials == (source,)
    assert uses[0].support == ()


@pytest.mark.parametrize("backend", ["api", "chatgpt_plan"])
def test_native_answer_drops_malformed_optional_passages_without_a_correction(monkeypatch, backend):
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("return", ["E1"])),
        reply({**answer("The value is seven. [E1]"),
               "citation_passages": [locator("E1", True, "The stated value is seven."),
                                     locator("E1", 1, "The stated value was seven."),
                                     locator("E1", 1, ""), {"ref": "E1"}]}),
    ], backend)
    result = ResearchSession(model=model, search=search, fetch=no_fetch).ask("What value is stated?")
    assert result.answer == "The value is seven. [1]"
    assert result.citation_uses[0].support == ()
    assert stages(payloads) == ["research", "research", "answer"]
    assert "citation_passages" not in json.dumps(result.trace)


def test_native_plan_answer_publishes_a_valid_passage(monkeypatch):
    excerpt = "The stated value is seven."
    model, payloads, _ = scripted(monkeypatch, [
        reply(initial(requests=[request()])), reply(initial("return", ["E1"])),
        reply({**answer("The source states seven. [E1]"),
               "citation_passages": [locator("E1", 1, excerpt)]}),
    ], "chatgpt_plan")
    result = ResearchSession(model=model, search=search, fetch=no_fetch).ask("What value is stated?")

    assert stages(payloads) == ["research", "research", "answer"]
    assert result.answer == "The source states seven. [1]"
    region, = result.citation_uses[0].support
    material, = result.citations[0].materials
    assert support_text(region, material) == excerpt
