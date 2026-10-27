"""Per-use binding, exact historical custody and actual Reader rendering."""

import json
import sqlite3
from dataclasses import replace
from hashlib import sha256

import pytest
from test_research_loop import Script, answer, decision, no_fetch, request

from scryraven import reading_room
from scryraven.presentation import source_body_html
from scryraven.session import ResearchSession
from scryraven.session_store import SessionStoreError, SQLiteSessionStore
from scryraven.sources import Evidence, SupportRegion

BODY = "Opening context.\n\nAlpha is seven.\n\nA consequential exception applies.\n\nOmega is nine.\n\nEnd context."
PARENT = Evidence("E1", "https://example.org/record", "Public record", BODY)
DRAFT = "Alpha is seven, with the stated exception. [E1]\n\nOmega is nine. [E1]"


def bound_result():
    """Historical fixture: saved coordinates predate this publication change."""
    from scryraven.results import CompletedAnswer, resolve_citations

    prose, citations, uses = resolve_citations(DRAFT, [PARENT], [PARENT], [])

    def region(text):
        start = BODY.index(text)
        return SupportRegion(PARENT.id, start, start + len(text),
                             sha256(BODY.encode()).hexdigest(), sha256(text.encode()).hexdigest())

    uses = (replace(uses[0], support=(region("Alpha is seven."),
                                    region("A consequential exception applies."))),
            replace(uses[1], support=(region("Omega is nine."),)))
    return None, CompletedAnswer(prose, "supported", "supported", (PARENT,), (), (PARENT,), citations, uses)


def saved_session(tmp_path):
    store = SQLiteSessionStore(tmp_path / "support.sqlite3")
    session = ResearchSession.create(store=store, engine=lambda question, **kwargs: bound_result()[1])
    session.ask("What are Alpha and Omega?")
    return store, session


def test_saved_coordinates_hashes_reopen_and_render_without_model_or_provider_io(tmp_path):
    store, session = saved_session(tmp_path)
    with sqlite3.connect(store.path) as db:
        payload_before = db.execute("SELECT payload FROM sessions").fetchone()[0]
    payload = json.loads(payload_before)
    supports = payload["turns"][0]["citation_uses"][0]["support"]
    assert set(supports[0]) == {"evidence_ref", "start_char", "end_char", "material_sha256", "passage_sha256"}
    assert supports[0]["material_sha256"] == sha256(BODY.encode()).hexdigest()
    assert not any(key in payload_before for key in ('"U1"', '"S1"', '"passage"', '"source_readings"'))
    reopened = ResearchSession.open(session.session_id, store=SQLiteSessionStore(store.path))
    assert reopened.turns == session.turns
    client = reading_room.create_app(store=store).test_client()
    html = client.get(f"/sessions/{session.session_id}").get_data(as_text=True)
    assert html.index("Open original publication") < html.index("Support for this citation")
    assert html.index("Support for this citation") < html.index("Surrounding context") < html.index("Full saved material")
    assert 'data-citation-start="' in html
    assert html.count('class="citation-support"') == 2
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT payload FROM sessions").fetchone()[0] == payload_before


@pytest.mark.parametrize("mutation", ["range", "hash", "passage_hash", "material", "partial"])
def test_corrupted_support_cannot_reopen_as_trusted_historical_support(tmp_path, mutation):
    store, session = saved_session(tmp_path)
    with sqlite3.connect(store.path) as db:
        payload = json.loads(db.execute("SELECT payload FROM sessions").fetchone()[0])
        use = payload["turns"][0]["citation_uses"][0]
        region = use["support"][0]
        if mutation == "range":
            region["end_char"] = len(BODY) + 1
        elif mutation == "hash":
            region["material_sha256"] = "0" * 64
        elif mutation == "passage_hash":
            region["passage_sha256"] = "0" * 64
        elif mutation == "material":
            region["evidence_ref"] = "E999"
        else:
            use.pop("support")
        db.execute("UPDATE sessions SET payload = ?", (json.dumps(payload),))
    with pytest.raises(SessionStoreError, match="invalid_session_data"):
        ResearchSession.open(session.session_id, store=store)


def test_old_turn_without_support_reopens_to_generic_inspection_without_rewrite(tmp_path):
    store, session = saved_session(tmp_path)
    with sqlite3.connect(store.path) as db:
        payload = json.loads(db.execute("SELECT payload FROM sessions").fetchone()[0])
        for use in payload["turns"][0]["citation_uses"]:
            use.pop("support")
        before = json.dumps(payload)
        db.execute("UPDATE sessions SET payload = ?", (before,))
    reopened = ResearchSession.open(session.session_id, store=store)
    assert all(not use.support for use in reopened.turns[0].citation_uses)
    html = reading_room.create_app(store=store).test_client().get(f"/sessions/{session.session_id}").get_data(as_text=True)
    assert "Support for this citation" not in html and "Material ScryRaven used" in html
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT payload FROM sessions").fetchone()[0] == before


def test_renderer_refuses_wrong_snapshot_coordinates_instead_of_showing_a_false_passage():
    _, result = bound_result()
    use = result.citation_uses[0]
    bad = SupportRegion("E1", 0, 4, "wrong", "wrong")
    assert "Support for this citation" not in source_body_html(result.citations[0], uses=(replace(use, support=(bad,)),))


def test_document_views_keep_exact_coordinates_and_original_pdf_action(tmp_path):
    from pdf_fixtures import text_pdf

    store = SQLiteSessionStore(tmp_path / "document.sqlite3")
    model = Script(decision(requests=[request("read", query="", target="D1", mode="local")]),
                   lambda packet: decision("return", [item["id"] for item in packet["evidence"]]),
                   answer("Alpha is seven. [D1] Omega is nine. [D1]"))
    session = ResearchSession.create(store=store, model=model, fetch=no_fetch)
    store.attach_document(session.session_id, 0, "public-fixture.pdf", "application/pdf",
                          text_pdf(["Alpha is seven.", "Omega is nine."]))
    session = ResearchSession.open(session.session_id, store=store, model=model, fetch=no_fetch)
    result = session.ask("What does the document state?")
    assert all(not use.support for use in result.citation_uses)
    assert all(item.id.startswith("D1@") and item.document_id == "D1"
               for item in result.selected_evidence)
    assert result.citations[0].page_start == 1 and result.citations[0].page_end == 2
    restored = ResearchSession.open(session.session_id, store=SQLiteSessionStore(store.path))
    assert restored.turns[0].citation_uses == result.citation_uses
    client = reading_room.create_app(store=store).test_client()
    html = client.get(f"/sessions/{session.session_id}").get_data(as_text=True)
    original = client.get(f"/sessions/{session.session_id}/documents/D1/original")
    assert original.status_code == 200 and original.data == restored.documents[0].original_pdf
    assert "Open original PDF" in html and "Support for this citation" not in html
    assert "Material ScryRaven used from this source" in html
