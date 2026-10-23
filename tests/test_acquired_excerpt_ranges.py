"""Explicit exact ranges of retained highlights preserve excerpt-level custody."""

import json
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest

from scryraven.acquisition import AcquisitionLibrary
from scryraven.answer_library import AnswerLibrary
from scryraven.errors import RunError
from scryraven.presentation import source_body_html
from scryraven.results import CompletedAnswer, resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SessionStoreError, SQLiteSessionStore
from scryraven.sources import Evidence, exact_view


def no_external():
    raise AssertionError("Explicit retained excerpt ranges must remain local")


def test_explicit_highlight_range_preserves_version_and_excerpt_coordinates():
    url = "https://example.org/report"
    old = Evidence("E1", url, "Old", "Old excerpt.", "provider_highlights")
    text = "Earlier text.\n\n[Separate provider highlight; intervening context omitted]\n\nRevenue 12; loss 13."
    parent = Evidence("E2", url, "New", text, "provider_highlights", "E1")
    library = AcquisitionLibrary((old, parent))
    start, end = text.index("Revenue"), len(text)
    result = library.execute({"kind": "read", "target": "E2", "mode": "local",
                              "start_char": start, "end_char": end}, before_external=no_external)
    view = library.materials[result["material_ids"][0]]
    assert result["local"] and not result["external"]
    assert view == exact_view(parent, start, end)
    assert view.parent_id == "E2" and view.source_id == "E1"
    assert view.content == "Revenue 12; loss 13."
    assert view.material()["range_basis"] == "acquired_highlight"
    assert result["read_receipt"]["range_basis"] == "acquired_highlight"
    assert "full_body_in_packet" not in result["read_receipt"]
    assert library.acquisitions == [old, parent] and not library.exposed
    repeated = library.execute({"kind": "read", "target": view.id, "mode": "local"},
                               before_external=no_external)
    assert repeated["material_ids"] == [view.id]


def test_short_explicit_highlight_range_uses_remaining_attention_only():
    text = "Unneeded text. " * 200 + "The 2018 revenue was 12 and loss was 13."
    parent = Evidence("E1", "https://example.org/report", "Report", text, "provider_highlights")
    library = AcquisitionLibrary((parent,))
    owner = AnswerLibrary(library, [], attention_characters=45)
    assert owner.deliver([parent.id])["evidence"] == []
    assert owner.refs == [] and owner.remaining == 45
    start, end = text.index("The 2018"), len(text)
    result = owner("library_read", json.dumps({"target": "E1", "focus": "",
                   "start_char": start, "end_char": end}))
    assert result["evidence"] == [exact_view(parent, start, end).material()]
    assert owner.remaining == 45 - (end - start)
    assert owner.refs == [f"E1@{start}:{end}"]
    assert library.exposed == set(owner.refs)
    assert owner.deliver([parent.id])["evidence"] == []


@pytest.mark.parametrize("start,end", [(True, 3), (0, False), (-1, 3), (3, 2), (0, 100)])
def test_invalid_highlight_ranges_never_create_views(start, end):
    parent = Evidence("E1", "https://example.org/report", "Report", "Exact excerpt", "provider_highlights")
    library = AcquisitionLibrary((parent,))
    result = library.execute({"kind": "read", "target": "E1", "mode": "local",
                              "start_char": start, "end_char": end}, before_external=no_external)
    assert result["status"] == "error" and result["code"] == "invalid_exact_range"
    assert list(library.materials) == ["E1"]
    with pytest.raises(ValueError, match="invalid_source_range"):
        exact_view(parent, start, end)


def test_highlight_view_citation_reopens_and_rejects_changed_basis_or_text(tmp_path):
    parent = Evidence("E1", "https://example.org/report", "Report", "Prefix. Exact fact. Tail.",
                      "provider_highlights")
    view = exact_view(parent, 8, 19)
    draft = f"Exact fact [{view.id}]"
    answer, citations, uses = resolve_citations(draft, [view], [parent], [])
    result = CompletedAnswer(answer, "supported", "supported", (parent,), (), (view,), citations, uses)
    store = SQLiteSessionStore(tmp_path / "excerpt.sqlite3")
    session = ResearchSession.create(store=store, engine=lambda question, **kwargs: result)
    session.ask("What does the retained excerpt say?")
    restored = ResearchSession.open(session.session_id, store=store)
    assert restored.turns[0].selected_evidence == (view,)
    assert restored.turns[0].citations[0].materials == (view,)
    assert restored.acquisitions == (parent,)
    html = source_body_html(restored.turns[0].citations[0])
    assert "Selected acquired excerpt" in html
    assert "original-page positions are unknown" in html
    assert "Exact fact." in html and "Prefix." not in html
    for forged in (replace(view, content="False fact."), replace(view, range_basis=None)):
        with pytest.raises(RunError, match="invalid_selected_material"):
            resolve_citations(draft, [forged], [parent], [])
    with closing(sqlite3.connect(store.path)) as connection:
        payload = json.loads(connection.execute("SELECT payload FROM sessions").fetchone()[0])
        payload["turns"][0]["selected_evidence"][0].pop("range_basis")
        connection.execute("UPDATE sessions SET payload = ?", (json.dumps(payload),))
        connection.commit()
    with pytest.raises(SessionStoreError, match="invalid_session_data"):
        store.load(session.session_id)


def test_range_basis_is_only_valid_for_web_targeted_views():
    with pytest.raises(ValueError, match="invalid_range_basis"):
        Evidence("E1", "https://example.org/report", "Report", "Exact", "provider_highlights",
                 range_basis="acquired_highlight")
