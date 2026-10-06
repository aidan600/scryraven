"""Exact selected-source completion; synthetic mechanics, not semantic quality."""

import json

import pytest
from pdf_fixtures import text_pdf
from test_pdf_documents import owned
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_loop import Script, answer, decision, no_fetch, request, search

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven.documents import document_views
from scryraven.research import RunLimits, _complete_selected_sources, run
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence, exact_view

tmp_path = external_tmp_path


def complete(seed, items, exposed=None, limit=128_000):
    materials = {item.id: item for item in items}
    return _complete_selected_sources(seed, materials, set(materials) if exposed is None else exposed, limit)


def receipt(result):
    return [event for event in result.trace if event["action"] == "answer_source_completion"]


def answer_ids(model):
    return [[item["id"] for item in call[2]["evidence"]]
            for call in model.calls if call[0] == "answer"]


def test_document_ranges_append_in_source_offset_order_after_unchanged_seed():
    document = owned(text_pdf(["First page.", "Second page.", "Third page."]))
    views = document_views(document, 0, document.text_character_count)
    other = document_views(owned(text_pdf(["Other document."]), document_id="D2"), 0, 15)
    # Material creation/exposure order does not control document order.
    items = [views[2], *other, views[1], views[0]]
    refs, diagnostic = complete([views[1].id, views[1].id], items)
    assert refs == [views[1].id, views[0].id, views[2].id]
    assert diagnostic == {"seed_refs": [views[1].id], "appended_refs": [views[0].id, views[2].id],
                          "evidence_characters": sum(len(view.content) for view in views), "status": "completed"}
    assert all(items[[item.id for item in items].index(ref)].content == view.content
               for ref, view in zip(refs, [views[1], views[0], views[2]]))


def test_web_versions_views_exact_dedup_source_order_and_unexposed_exclusion():
    first = Evidence("E1", "https://example.org/a", "Same title", "Older first-source text.")
    second = Evidence("E2", "https://example.org/b", "Same title", "Second source text.")
    newer = Evidence("E10", first.url, first.title, "Newer first-source text.", source_id="E1")
    unseen = Evidence("E11", first.url, first.title, "Unexposed same-source text.", source_id="E1")
    other = Evidence("E12", "https://example.org/a/similar", first.title, first.content)
    second_newer = Evidence("E3", second.url, second.title, "Second-source new text.", source_id="E2")
    views = [exact_view(first, 6, 12), exact_view(first, 0, 6)]
    items = [newer, unseen, other, *views, second_newer, second, first]
    exposed = {item.id for item in items} - {unseen.id}
    seed = [second_newer.id, newer.id, second_newer.id]
    refs, _ = complete(seed, items, exposed)
    assert refs == ["E3", "E10", "E2", "E1", views[1].id, views[0].id]
    assert seed == ["E3", "E10", "E3"]
    assert unseen.id not in refs and other.id not in refs
    # Never replace a selected view with its unexposed full parent.
    refs, _ = complete([views[0].id], items, {views[0].id, views[1].id})
    assert refs == [views[0].id, views[1].id]


def test_no_op_preserves_exact_packet_membership_order_and_bytes():
    items = [Evidence("E1", "https://example.org/a", "A", "Exact \n text."),
             Evidence("E2", "https://example.org/b", "B", "Other text.")]
    for seed in ([], ["E2", "E1"]):
        before = json.dumps([next(item.material() for item in items if item.id == ref) for ref in seed])
        refs, diagnostic = complete(seed, items)
        assert refs == seed
        assert json.dumps([next(item.material() for item in items if item.id == ref) for ref in refs]) == before
        assert diagnostic["status"] == "no_op" and diagnostic["appended_refs"] == []


@pytest.mark.parametrize("characters,status", [(128_000, "completed"), (128_001, "skipped_over_attention")])
def test_full_completion_at_attention_boundary_is_all_or_nothing(characters, status):
    seed = Evidence("E1", "https://example.org/a", "A", "x" * 60_000)
    small = Evidence("E2", seed.url, "A", "y", source_id=seed.source_id)
    large = Evidence("E3", seed.url, "A", "z" * (characters - 60_001), source_id=seed.source_id)
    refs, diagnostic = complete([seed.id], [seed, small, large])
    assert diagnostic["status"] == status
    assert refs == (["E1", "E2", "E3"] if status == "completed" else ["E1"])
    assert diagnostic["evidence_characters"] == (characters if status == "completed" else 60_000)
    assert diagnostic["appended_refs"] == (["E2", "E3"] if status == "completed" else [])


def test_explicit_handoff_cites_appended_material_and_preserves_historical_custody(tmp_path):
    second_text = "Seven under the stated condition."
    second_read = decision(requests=[request("read", query="", target="E1", mode="full")])
    model = Script(decision(), second_read, decision("answer", ["E2"]), answer())
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(store=store, model=model, search=search,
                                     fetch=lambda url: FetchedMaterial(url, second_text))
    result = session.ask("Value?")
    assert answer_ids(model) == [["E2", "E1"]]
    assert receipt(result)[0]["seed_refs"] == ["E2"]
    assert receipt(result)[0]["appended_refs"] == ["E1"]
    # Existing canonical-source citations snapshot every supplied exact material
    # in that cited group, including unused same-source Answer context.
    assert result.selected_evidence == (result.evidence[1], result.evidence[0])
    assert result.citations[0].source_id == "E1"
    assert result.citations[0].materials == result.selected_evidence
    assert len(session.acquisitions) == 2
    before = session.turns[0]
    reopened = ResearchSession.open(session.session_id, store=store, model=Script(
        decision(requests=[request("read", query="", target="E2", mode="local")]),
        decision("answer", ["E2"]),
        answer("Seven under the stated condition. [E2]", readings=[
            {"evidence_ref": "E2", "passages": [second_text]}])), search=search, fetch=no_fetch)
    later = reopened.ask("What is the condition?")
    assert reopened.turns[0] == before
    assert reopened.acquisitions == session.acquisitions
    assert [item.id for item in later.selected_evidence] == ["E2", "E1"]
    assert ResearchSession.open(session.session_id, store=store).turns == reopened.turns


def test_pdf_session_handoff_appends_only_exposed_exact_views(tmp_path):
    store = SQLiteSessionStore(tmp_path / "documents.sqlite3")
    session = ResearchSession.create(store=store)
    data = text_pdf(["First page.", "Second page.", "Unexposed third page."])
    attached = store.attach_document(session.session_id, 0, "report.pdf", "application/pdf", data)
    document = attached.document
    views = document_views(document, 0, document.text_character_count)
    model = Script(
        decision(requests=[{**request("read", query="", target="D1", mode="local"),
                            "start_char": 0, "end_char": views[1].end_char}]),
        decision("answer", [views[1].id]),
        answer(f"First page. [{views[0].id}]", readings=[
            {"evidence_ref": views[0].id, "passages": ["First page."]}]))
    session = ResearchSession.open(session.session_id, store=store, model=model, search=no_fetch, fetch=no_fetch)
    result = session.ask("Takeaways?")
    assert answer_ids(model) == [[views[1].id, views[0].id]]
    assert views[2].id not in answer_ids(model)[0]
    assert result.evidence == ()
    assert result.selected_evidence == (views[1], views[0])
    assert result.citations[0].source_id == "D1"
    assert ResearchSession.open(session.session_id, store=store).turns == session.turns


@pytest.mark.parametrize("bound", ["semantic_attempts", "answer_deadline_reserve"])
def test_terminal_handoff_completes_after_pending_delivery(bound):
    now = [0.0]
    old = Evidence("E1", "https://example.org/fact", "Fact", "The stated value is seven.", "provider_highlights")
    def fetch(url):
        if bound == "answer_deadline_reserve":
            now[0] = 121
        return FetchedMaterial(url, "Seven with a qualification.")
    model = Script(decision(requests=[request("read", query="", target="E1", mode="full")]), answer())
    result = run("Value?", model=model, retained_acquisitions=(old,), initial_evidence=(old,),
                 fetch=fetch, limits=RunLimits(semantic_attempts=2 if bound == "semantic_attempts" else 12),
                 clock=lambda: now[0])
    assert answer_ids(model) == [["E2", "E1"]]
    assert result.stop_reason == "research_bound"
    assert any(event["action"] == "research_bound" and event["code"] == bound for event in result.trace)
    # Research shelved E1; pending E2 is the ordinary seed and E1 appends.
    assert receipt(result)[-1]["seed_refs"] == ["E2"]
    assert receipt(result)[-1]["appended_refs"] == ["E1"]


@pytest.mark.parametrize("terminal", [False, True])
def test_missing_information_new_same_source_material_defeats_no_progress(terminal):
    third_text = "A new qualification."
    model = Script(decision(), decision("answer", ["E1"]),
                   answer("A fragment. [E1]", "partial", "What condition applies?"),
                   decision(refs=["E1"], requests=[request("read", query="", target="E1", mode="full")]),
                   decision("answer", ["E1"]),
                   answer("A new qualification. [E2]", readings=[{"evidence_ref": "E2", "passages": [third_text]}]))
    if terminal:
        model = Script(*list(model.outputs)[:4],
                       answer("A new qualification. [E2]", readings=[{"evidence_ref": "E2", "passages": [third_text]}]))
    result = run("Value?", model=model, search=search, fetch=lambda url: FetchedMaterial(url, third_text),
                 limits=RunLimits(semantic_attempts=5 if terminal else 12))
    assert answer_ids(model) == [["E1"], (["E2", "E1"] if terminal else ["E1", "E2"])]
    assert not any(event["action"] == "answer_committed_no_progress" for event in result.trace)
    assert {item.id for item in result.selected_evidence} == {"E1", "E2"}
    assert result.posture == "supported"


@pytest.mark.parametrize("terminal", [False, True])
def test_unchanged_completed_packet_preserves_no_progress_and_research_attention(terminal):
    model = Script(decision(),
                   decision(requests=[request("read", query="", target="E1", mode="full")]),
                   decision("answer", ["E2"]),
                   answer("A fragment. [E1]", "partial", "What condition applies?"),
                   (decision(refs=["E2"], requests=[request("read", query="", target="E2", mode="local")])
                    if terminal else decision("answer", ["E2"])))
    result = run("Value?", model=model, search=search,
                 fetch=lambda url: FetchedMaterial(url, "Seven with a qualification."),
                 limits=RunLimits(semantic_attempts=6 if terminal else 12))
    assert answer_ids(model) == [["E2", "E1"]]
    assert [item["id"] for item in model.calls[-1][2]["evidence"]] == ["E2"]
    committed = next(event for event in result.trace if event["action"] == "answer_committed_no_progress")
    assert committed["prior_selected_refs"] == committed["selected_refs"] == ["E2", "E1"]
    assert result.posture == "partial"
    for event in receipt(result):
        assert set(event) == {"stage", "action", "seed_refs", "appended_refs", "evidence_characters", "status"}


def test_over_limit_handoff_preserves_seed_and_existing_citation_boundary():
    old_text = "Old exact fact.".ljust(32_000, "x")
    old = Evidence("E1", "https://example.org/fact", "Fact", old_text, "provider_highlights")
    second = Evidence("E2", old.url, old.title, "y" * 32_000, "provider_highlights", "E1")
    new_text = "New exact fact.".ljust(2_000, "z")
    model = Script(decision(), decision("answer", ["E3"]),
                   answer("New exact fact. [E3]", readings=[{"evidence_ref": "E3", "passages": [new_text]}]))
    result = run("Value?", model=model, retained_acquisitions=(old, second), initial_evidence=(old, second),
                 search=lambda query: [DiscoveryCandidate(old.title, old.url, new_text, context_kind="provider_highlights")],
                 fetch=no_fetch, limits=RunLimits(attention_characters=65_536))
    assert answer_ids(model) == [["E3"]]
    assert receipt(result)[0]["status"] == "skipped_over_attention"
    assert receipt(result)[0]["appended_refs"] == []
    assert [item.id for item in result.selected_evidence] == ["E3"]
    assert result.citations[0].source_id == "E1" and len(result.citations[0].materials) == 1
