"""Per-use binding, exact historical custody and actual Reader rendering."""

import json
import sqlite3
from dataclasses import replace
from hashlib import sha256

import pytest
from test_research_loop import Script, answer, decision, no_fetch, request

from scryraven import reading_room
from scryraven.presentation import source_body_html
from scryraven.research import run
from scryraven.session import ResearchSession
from scryraven.session_store import SessionStoreError, SQLiteSessionStore
from scryraven.sources import Evidence, SupportRegion, support_text
from scryraven.support import bind_support, localization_packet, region_spans

BODY = "Opening context.\n\nAlpha is seven.\n\nA consequential exception applies.\n\nOmega is nine.\n\nEnd context."
PARENT = Evidence("E1", "https://example.org/record", "Public record", BODY)
DRAFT = "Alpha is seven, with the stated exception. [E1]\n\nOmega is nine. [E1]"


class BoundModel(Script):
    def __init__(self, binding=None):
        super().__init__(decision(requests=[request("read", query="", target="E1", mode="local")]),
                         decision("answer", ["E1"]), answer(DRAFT),
                         answer("Legacy fact. [E1]", readings=[{"evidence_ref": "E1", "passages": ["Alpha is seven."]}]))
        self.binding = binding

    def __call__(self, stage, prompt, material, schema):
        if stage != "localize":
            return super().__call__(stage, prompt, material, schema)
        self.calls.append((stage, prompt, material, schema))
        if self.binding is not None:
            return json.dumps(self.binding)
        ids = {row["text"].strip(): row["id"] for row in material["regions"]}
        return json.dumps({"U1": [ids["Alpha is seven."], ids["A consequential exception applies."]],
                           "U2": [ids["Omega is nine."]]})


def bound_result(binding=None):
    model = BoundModel(binding)
    result = run("What are Alpha and Omega?", model=model, retained_acquisitions=(PARENT,), fetch=no_fetch)
    return model, result


@pytest.mark.parametrize("text", [BODY, "x" * 7000, "🙂 e\u0301\r\n" * 800, "   \n\n", ""])
def test_regions_partition_all_exact_saved_characters_without_ranking(text):
    spans = list(region_spans(text))
    assert "".join(text[start:end] for start, end in spans) == text
    assert all(0 < end - start <= 1200 for start, end in spans)
    assert all(left[1] == right[0] for left, right in zip(spans, spans[1:]))


def test_repeated_source_uses_bind_different_noncontiguous_regions_after_answer():
    model, result = bound_result()
    assert [call[0] for call in model.calls] == ["research", "research", "answer", "localize"]
    packet = model.calls[-1][2]
    assert packet["answer"] == result.answer
    assert "".join(row["text"] for row in packet["regions"]) == BODY
    assert set(model.calls[-1][3]["properties"]) == {"U1", "U2"}
    first, second = result.citation_uses
    assert [support_text(region, PARENT).strip() for region in first.support] == [
        "Alpha is seven.", "A consequential exception applies."]
    assert [support_text(region, PARENT).strip() for region in second.support] == ["Omega is nine."]
    assert first.number == second.number == 1
    assert result.answer == DRAFT.replace("[E1]", "[1]")


@pytest.mark.parametrize("binding", [
    {"U1": [], "U2": ["S7"]},
    {"U1": ["S999"], "U2": ["S7"]},
    {"U1": ["S3"]},
    {"U1": ["S3"], "U2": ["S7"], "quotation": "INVENTED_TEXT"},
    {"U1": ["S3", "S3"], "U2": ["S7"]},
])
def test_failed_binding_publishes_only_the_existing_legacy_fallback(binding):
    model, result = bound_result(binding)
    assert result.answer == "Legacy fact. [1]"
    assert all(not use.support for use in result.citation_uses)
    assert model.calls[-1][0] == "answer" and "source_readings" in model.calls[-1][3]["properties"]
    assert DRAFT not in json.dumps(model.calls[-1][2])
    assert any(event["action"] == "answer_legacy_fallback" for event in result.trace)


def test_cross_source_id_and_wrong_version_coordinates_are_rejected():
    from scryraven.results import resolve_citations

    other = Evidence("E2", "https://example.org/other", "Other", "Other actual fact.")
    prose, citations, uses = resolve_citations("First [E1]. Other [E2].", [PARENT, other], [PARENT, other], [])
    packet, addresses, shape = localization_packet(prose, citations, uses)
    wrong_source = next(row["id"] for row in packet["regions"] if row["source_id"] == "E2")
    with pytest.raises(ValueError, match="invalid_support_region"):
        bind_support(shape.model_validate({"U1": [wrong_source], "U2": [wrong_source]}),
                     packet, addresses, citations, uses)
    region = next(iter(addresses.values()))
    with pytest.raises(ValueError, match="invalid_support_coordinates"):
        support_text(region, replace(PARENT, content="changed version"))


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
                   lambda packet: decision("answer", [item["id"] for item in packet["evidence"]]),
                   answer("Alpha is seven. [D1] Omega is nine. [D1]"))
    session = ResearchSession.create(store=store, model=model, fetch=no_fetch)
    store.attach_document(session.session_id, 0, "public-fixture.pdf", "application/pdf",
                          text_pdf(["Alpha is seven.", "Omega is nine."]))
    session = ResearchSession.open(session.session_id, store=store, model=model, fetch=no_fetch)
    result = session.ask("What does the document state?")
    assert all(use.support for use in result.citation_uses)
    selected = {item.id: item for item in result.selected_evidence}
    for use in result.citation_uses:
        for region in use.support:
            assert support_text(region, selected[region.evidence_ref])
            assert region.evidence_ref.startswith("D1@")
    restored = ResearchSession.open(session.session_id, store=SQLiteSessionStore(store.path))
    assert restored.turns[0].citation_uses == result.citation_uses
    html = reading_room.create_app(store=store).test_client().get(f"/sessions/{session.session_id}").get_data(as_text=True)
    assert "Open original PDF" in html and "Support for this citation" in html
