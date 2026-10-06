"""PDF document custody, local navigation, citations, and Reading Room boundaries."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from pdf_fixtures import encrypted_pdf, text_pdf
from test_exa_deep_bootstrap import production_post
from test_persistent_sessions import tmp_path as external_tmp_path
from test_reading_room import app_for, token
from test_research_loop import Script, answer, decision, request

from core.exa_transport import DEFAULT_DISCOVERY_RESULT_COUNT
from scryraven import documents
from scryraven.documents import (
    ALREADY_ATTACHED_NOTICE,
    MAX_EXTRACTED_CHARACTERS,
    MAX_FILENAME_LENGTH,
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    TEXT_ONLY_WARNING,
    DocumentRejected,
    SessionDocument,
    content_disposition,
    document_text_view,
    document_views,
    index_parent,
    prepare_pdf,
    sanitize_filename,
    textless_page_warning,
)
from scryraven.dogfood_diagnostics import TurnDiagnostics
from scryraven.presentation import Citation, document_page_label, render_cli, source_body_html
from scryraven.research import RunLimits, run
from scryraven.results import resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SessionStoreError, SQLiteSessionStore
from scryraven.sources import (
    EXPANSION_CHARACTERS,
    PACKET_CHARACTERS,
    TARGETED_SOURCE_CHARACTERS,
    Evidence,
    SourceIndex,
)

tmp_path = external_tmp_path

PAGE_FACT = "The reported revenue was 184 million dollars."
FILLER = "The cafeteria menu lists soup and bread. "
QUALIFICATION = (
    "The revenue figure uses the fiscal year 1998 denominator and excludes discontinued operations."
)
CRANE = "The crane count is 14."
SPARE = "The crane count excludes spare units."
HARBOR = "The harbor depth is twelve meters."
BERTH = "The berth clearance is nine meters."


def owned(data: bytes, filename: str = "report.pdf", document_id: str = "D1") -> SessionDocument:
    prepared = prepare_pdf(filename, "application/pdf", data)
    return SessionDocument(
        document_id, prepared.filename, prepared.media_type, prepared.byte_length, prepared.sha256,
        datetime.now(timezone.utc).isoformat(), prepared.page_count, prepared.text_character_count,
        prepared.textless_page_count, prepared.pages, prepared.original_pdf,
    )


def reject(filename, media_type, data):
    with pytest.raises(DocumentRejected) as caught:
        prepare_pdf(filename, media_type, data)
    assert str(caught.value) == caught.value.code
    assert "Traceback" not in str(caught.value) and "pypdf" not in str(caught.value)
    return caught.value.code


def no_provider(*_args, **_kwargs):
    raise AssertionError("provider I/O")


def payload_of(path, session_id):
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute("SELECT payload FROM sessions WHERE session_id = ?", (session_id,)).fetchone()[0]


def document_rows(path, session_id=None):
    with closing(sqlite3.connect(path)) as connection:
        if session_id is None:
            return connection.execute("SELECT session_id, document_id, original_pdf FROM session_documents").fetchall()
        return connection.execute(
            "SELECT document_id, original_pdf, pages_json FROM session_documents WHERE session_id = ?",
            (session_id,),
        ).fetchall()


def upload(client, location, pdf, filename="report.pdf", headers=None):
    action = "/documents" if location == "/" else location + "/documents"
    fields = token(client.get(location), action)
    return client.post(action, data={
        "form_token": fields["form_token"],
        "pdf": (BytesIO(pdf), filename, "application/pdf"),
    }, headers=headers)


def test_operating_bounds_and_prompt_limits_stay_in_place():
    limits = RunLimits()
    assert DEFAULT_DISCOVERY_RESULT_COUNT == 6
    assert (limits.semantic_attempts, limits.external_attempts, limits.seconds, limits.attention_characters) == (
        12, 16, 300, 128_000)
    assert (TARGETED_SOURCE_CHARACTERS, PACKET_CHARACTERS, EXPANSION_CHARACTERS) == (32_000, 32_000, 48_000)
    assert (MAX_PDF_BYTES, MAX_PDF_PAGES, MAX_EXTRACTED_CHARACTERS) == (20 * 1024 * 1024, 500, 2_000_000)
    from scryraven.research import ANSWER_PROMPT, RESEARCH_PROMPT
    assert "Read target=D#" in RESEARCH_PROMPT
    assert "not Evidence" in RESEARCH_PROMPT
    assert "true outside the" in ANSWER_PROMPT and "document's claim distinct" in ANSWER_PROMPT
    assert "Images and scanned content are not supplied" in ANSWER_PROMPT


def test_ingestion_accepts_text_pages_and_rejects_unusable_pdfs(monkeypatch):
    one = prepare_pdf("notes.pdf", "application/pdf", text_pdf(["caf\u00e9 costs \u00a35"]))
    assert one.pages == ("caf\u00e9 costs \u00a35",) and one.page_count == 1 and one.textless_page_count == 0
    mixed = prepare_pdf(r"C:\secret\annual<script>.pdf", "application/octet-stream", text_pdf([PAGE_FACT, ""]))
    assert mixed.filename == "annual<script>.pdf"
    assert mixed.pages == (PAGE_FACT, "") and mixed.textless_page_count == 1
    assert textless_page_warning(1) == "1 page contained no extractable text."
    assert "page" in textless_page_warning(12) and "image" not in textless_page_warning(12).casefold()
    multi = prepare_pdf("report.pdf", "application/pdf", text_pdf([PAGE_FACT, QUALIFICATION]))
    assert multi.page_count == 2 and multi.pages == (PAGE_FACT, QUALIFICATION)
    assert "".join(multi.pages) == multi.pages[0] + multi.pages[1]
    assert "Page " not in "".join(multi.pages)

    assert reject("notes.pdf", "application/pdf", b"%PDF-1.4\nnot a pdf") == "pdf_malformed"
    assert reject("locked.pdf", "application/pdf", encrypted_pdf([PAGE_FACT])) == "pdf_encrypted"
    assert reject("scan.pdf", "application/pdf", text_pdf([""])) == "pdf_no_text"
    assert TEXT_ONLY_WARNING in documents.DOCUMENT_ERROR_MESSAGES["pdf_no_text"]
    assert reject("notes.txt", "text/plain", text_pdf([PAGE_FACT])) == "pdf_type_rejected"
    assert reject("", "application/pdf", text_pdf([PAGE_FACT])) == "pdf_required"
    assert reject("big.pdf", "application/pdf", b"%PDF-" + b"0" * (MAX_PDF_BYTES - 4)) == "pdf_too_large"
    assert len(b"%PDF-" + b"0" * (MAX_PDF_BYTES - 4)) == MAX_PDF_BYTES + 1
    assert reject("long.pdf", "application/pdf", text_pdf(["x"] * (MAX_PDF_PAGES + 1))) == "pdf_too_many_pages"
    monkeypatch.setattr(documents, "MAX_EXTRACTED_CHARACTERS", 12)
    assert reject("dense.pdf", "application/pdf", text_pdf(["x" * 13])) == "pdf_too_much_text"
    safe_name = content_disposition("annual<script>.pdf")
    assert "<" not in safe_name and ">" not in safe_name
    assert "\r" not in safe_name and "\n" not in safe_name
    assert sanitize_filename(r"..\..\secret.pdf") == "secret.pdf"
    assert len(sanitize_filename("a" * 400 + ".pdf")) <= MAX_FILENAME_LENGTH


def test_page_mapping_does_not_glue_adjacent_pages():
    document = owned(text_pdf(["PAGEONEEND", "PAGETWOSTART"]))
    assert document.extracted_text == "PAGEONEENDPAGETWOSTART"
    assert document.interior_boundaries == (len("PAGEONEEND"),)
    views = document_views(document, 0, len(document.extracted_text))
    assert [view.content for view in views] == ["PAGEONEEND", "PAGETWOSTART"]
    assert [(view.page_start, view.page_end) for view in views] == [(1, 1), (2, 2)]
    parent = index_parent(document)
    regions = SourceIndex(parent, document.interior_boundaries).regions
    assert all("PAGEONEENDPAGETWOSTART" not in parent.content[start:end] for start, end in regions)
    exact = document_text_view(document, 0, len("PAGEONEEND"))
    assert document_text_view(document, exact.start_char, exact.end_char) == exact
    with pytest.raises(ValueError):
        document_text_view(document, len("PAGEONEEND") - 2, len("PAGEONEEND") + 2)


def test_fresh_schema_and_version_one_migration_preserve_payloads(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    store = SQLiteSessionStore(path)
    created = store.create("Existing")
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'session_documents'").fetchone()[0] == "session_documents"
    before = path.read_bytes()
    assert SQLiteSessionStore(path).load(created.metadata.session_id) == created
    assert path.read_bytes() == before

    legacy = tmp_path / "legacy.sqlite3"
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    session_id = "a" * 32
    stamp = "2020-01-01T00:00:00+00:00"
    with closing(sqlite3.connect(legacy)) as connection:
        connection.execute(
            "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL, title TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL)")
        connection.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
                           (session_id, stamp, stamp, "Historical", 1, payload))
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    legacy_before = legacy.read_bytes()
    migrated = SQLiteSessionStore(legacy).load(session_id)
    assert migrated.metadata.revision == 1 and migrated.documents == () and migrated.state.turns
    with closing(sqlite3.connect(legacy)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT payload FROM sessions").fetchone()[0] == payload
        assert connection.execute("SELECT count(*) FROM session_documents").fetchone()[0] == 0
    assert legacy.read_bytes() != legacy_before

    newer = tmp_path / "newer.sqlite3"
    with closing(sqlite3.connect(newer)) as connection:
        connection.execute("CREATE TABLE sessions (session_id TEXT PRIMARY KEY, payload TEXT)")
        connection.execute("INSERT INTO sessions VALUES (?, ?)", (session_id, payload))
        connection.execute("PRAGMA user_version = 3")
        connection.commit()
    frozen = newer.read_bytes()
    with pytest.raises(SessionStoreError) as caught:
        SQLiteSessionStore(newer).load(session_id)
    assert caught.value.code == "incompatible_session_store"
    assert newer.read_bytes() == frozen


def test_attachment_is_not_a_turn_and_stays_inside_one_session(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    store = SQLiteSessionStore(path)
    first = store.create()
    blank = text_pdf([PAGE_FACT, ""])
    attached = store.attach_document(first.metadata.session_id, 0, r"..\report.pdf", "application/pdf", blank)
    assert attached.created and attached.document.document_id == "D1"
    saved = store.load(first.metadata.session_id)
    assert saved.metadata.revision == 0 and saved.state.turns == ()
    assert saved.metadata.updated_at >= first.metadata.updated_at
    assert saved.documents[0].filename == "report.pdf"
    assert saved.documents[0].original_pdf == blank and saved.documents[0].pages == (PAGE_FACT, "")
    payload = payload_of(path, first.metadata.session_id)
    assert "original_pdf" not in payload and PAGE_FACT not in payload and blank.hex() not in payload
    reopened = SQLiteSessionStore(path).load(first.metadata.session_id)
    assert reopened.documents == saved.documents and reopened.metadata.revision == 0

    duplicate = store.attach_document(first.metadata.session_id, 0, "other-name.pdf", "application/pdf", blank)
    assert duplicate.created is False and duplicate.document == attached.document
    assert store.load(first.metadata.session_id).metadata.updated_at == saved.metadata.updated_at
    assert len(document_rows(path, first.metadata.session_id)) == 1

    other = text_pdf([QUALIFICATION])
    second = store.attach_document(first.metadata.session_id, 0, "later.pdf", "application/pdf", other)
    assert second.created and second.document.document_id == "D2"
    assert [item.document_id for item in store.load(first.metadata.session_id).documents] == ["D1", "D2"]

    other_session = store.create()
    copied = store.attach_document(other_session.metadata.session_id, 0, "report.pdf", "application/pdf", blank)
    assert copied.document.document_id == "D1" and copied.document.sha256 == attached.document.sha256
    assert copied.document is not attached.document
    store.delete(first.metadata.session_id, revision=0)
    with pytest.raises(SessionStoreError) as missing:
        store.load(first.metadata.session_id)
    assert missing.value.code == "session_not_found"
    assert [row[0] for row in document_rows(path)] == [other_session.metadata.session_id]
    assert store.load(other_session.metadata.session_id).documents[0].original_pdf == blank

    failed = store.create()
    before = store.load(failed.metadata.session_id)
    before_payload = payload_of(path, failed.metadata.session_id)
    assert reject("broken.pdf", "application/pdf", b"%PDF-bad") == "pdf_malformed"
    with pytest.raises(DocumentRejected):
        store.attach_document(failed.metadata.session_id, 0, "broken.pdf", "application/pdf", b"%PDF-bad")
    assert store.load(failed.metadata.session_id) == before
    assert payload_of(path, failed.metadata.session_id) == before_payload


def test_attach_after_turns_does_not_rewrite_them(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    session = ResearchSession.create(
        store=store, model=Script(decision("answer"), answer("An answer was not established.", "unable")),
        search=no_provider, fetch=no_provider, lexical_search=no_provider)
    session.ask("What remains unsettled?")
    before = store.load(session.session_id)
    before_payload = payload_of(store.path, session.session_id)
    pdf = text_pdf([PAGE_FACT])
    attached = store.attach_document(session.session_id, 1, "after.pdf", "application/pdf", pdf)
    saved = store.load(session.session_id)
    assert saved.metadata.revision == 1 and saved.state.turns == before.state.turns
    assert saved.documents == (attached.document,)
    assert payload_of(store.path, session.session_id) == before_payload
    with pytest.raises(DocumentRejected):
        store.attach_document(session.session_id, 1, "broken.pdf", "application/pdf", b"%PDF-nope")
    assert store.load(session.session_id) == saved


def test_local_read_and_find_stay_bounded_and_off_provider_budget():
    filler = FILLER * 1200
    document = owned(text_pdf([PAGE_FACT, filler, QUALIFICATION]), filename="annual-report.pdf")
    assert document.text_character_count > PACKET_CHARACTERS
    assert document.extracted_text.index(QUALIFICATION) > PACKET_CHARACTERS
    observations = []
    diagnostics = TurnDiagnostics()

    def observe(event):
        observations.append(event)
        diagnostics.observe(event)

    def choose(material):
        assert material["evidence"] == []
        encoded = json.dumps(material["catalog"])
        assert QUALIFICATION not in encoded and PAGE_FACT not in encoded and filler not in encoded
        row = material["catalog"]["documents"][0]
        assert row == {
            "id": "D1", "filename": "annual-report.pdf", "media_type": "application/pdf",
            "pages": 3, "characters": document.text_character_count, "source_kind": "user_document",
            "visual_analysis": False, "textless_page_count": 0,
        }
        assert "%PDF" not in encoded
        return decision(requests=[request("read", query="", target="D1", mode="local", focus="fiscal year 1998 denominator")])

    def select(material):
        item = next(entry for entry in material["evidence"] if QUALIFICATION in entry["content"])
        assert item["page_start"] == item["page_end"] == 3
        assert item["source_kind"] == "user_document" and item["url"] == ""
        assert document.extracted_text not in json.dumps(material)
        assert all(len(entry["content"]) <= TARGETED_SOURCE_CHARACTERS for entry in material["evidence"])
        assert all("PAGEONEENDPAGETWOSTART" not in entry["content"] for entry in material["evidence"])
        return decision("answer", [item["id"]])

    def respond(material):
        item = material["evidence"][0]
        return answer(
            f"The report's revenue figure uses the fiscal year 1998 denominator. [{item['id']}]",
            readings=[{"evidence_ref": item["id"], "passages": [QUALIFICATION]}],
        )

    result = run(
        "What revenue figure does the report give, and what scope does it use?",
        model=Script(choose, select, respond), documents=(document,), observe=observe,
        search=no_provider, fetch=no_provider, lexical_search=no_provider,
    )
    assert result.trace[-1]["budget"]["external_attempts"] == 0
    assert result.evidence == ()
    assert result.selected_evidence[0].content.find(QUALIFICATION) >= 0
    assert result.selected_evidence[0].page_start == 3
    assert result.citations[0].url == "" and result.citations[0].filename == "annual-report.pdf"
    receipt = next(event["result"]["read_receipt"] for event in result.trace
                   if event["action"] == "acquisition_result" and event["result"].get("read_receipt"))
    assert receipt["full_body_in_packet"] is False
    assert receipt["returned_characters"] <= PACKET_CHARACTERS
    assert receipt["returned_characters"] < document.text_character_count
    navigation = next(event["document_navigation"] for event in observations
                      if event["action"] == "acquisition_timing" and "document_navigation" in event)
    assert navigation["document_count"] == 1
    assert navigation["local_read_packet_characters"] == receipt["returned_characters"]
    assert navigation["candidate_regions_considered"] > 0
    diagnostic = json.dumps(diagnostics.acquisitions)
    assert "annual-report.pdf" not in diagnostic and QUALIFICATION not in diagnostic
    assert diagnostics.sizes["document_count"] == 1
    assert diagnostics.sizes["document_character_count"] == document.text_character_count


def test_find_keeps_document_and_web_identities_distinct():
    document = owned(text_pdf([PAGE_FACT, FILLER * 1200, QUALIFICATION]))
    web = Evidence("E1", "https://example.test/harbor", "Harbor notice", HARBOR)

    def choose(material):
        item = next(entry for entry in material["evidence"] if QUALIFICATION in entry["content"])
        assert item["page_start"] == 3 and item["document_id"] == "D1" and item["url"] == ""
        assert document.extracted_text not in json.dumps(material)
        return decision("answer", [item["id"]])

    def respond(material):
        item = material["evidence"][0]
        return answer(f"The denominator is fiscal year 1998. [{item['id']}]",
                      readings=[{"evidence_ref": item["id"], "passages": [QUALIFICATION]}])

    scoped = request("find", query="fiscal year 1998 denominator")
    scoped["scope"] = ["D1"]
    found = run("Where is the denominator?", model=Script(
        decision(requests=[scoped]), choose, respond), documents=(document,),
        search=no_provider, fetch=no_provider, lexical_search=no_provider)
    assert found.trace[-1]["budget"]["external_attempts"] == 0
    assert found.citations[0].page_end == 3 and QUALIFICATION in found.selected_evidence[0].content
    assert all(item.source_id == "D1" for item in found.selected_evidence)

    def inspect(material):
        contents = {entry["content"] for entry in material["evidence"]}
        assert any(HARBOR in content for content in contents)
        assert any(BERTH in content for content in contents)
        web_items = [entry for entry in material["evidence"] if entry["url"].startswith("https://")]
        document_items = [entry for entry in material["evidence"] if entry.get("source_kind") == "user_document"]
        assert web_items and document_items
        assert {item["source_id"] for item in web_items} == {"E1"}
        assert {item["source_id"] for item in document_items} == {"D1"}
        assert all(HARBOR not in item["content"] or BERTH not in item["content"] for item in material["evidence"])
        return decision("answer", [document_items[0]["id"]])

    def respond_berth(material):
        item = material["evidence"][0]
        return answer(f"The document says nine meters. [{item['id']}]",
                      readings=[{"evidence_ref": item["id"], "passages": [BERTH]}])

    unscoped = request("find", query="meters")
    mixed = run("Locate both notices.", model=Script(decision(requests=[unscoped]), inspect, respond_berth),
                documents=(owned(text_pdf([BERTH])),), retained_acquisitions=(web,),
                search=no_provider, fetch=no_provider, lexical_search=no_provider)
    assert mixed.trace[-1]["budget"]["external_attempts"] == 0
    assert mixed.evidence == (web,)


def test_followup_reopens_the_same_document_without_reupload(tmp_path):
    pdf = text_pdf([CRANE, SPARE])
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    created = store.create()
    store.attach_document(created.metadata.session_id, 0, "cranes.pdf", "application/pdf", pdf)
    document = store.load(created.metadata.session_id).documents[0]

    def select(material):
        item = next(entry for entry in material["evidence"] if CRANE in entry["content"])
        return decision("answer", [item["id"]])

    def respond(material):
        item = material["evidence"][0]
        return answer(f"The document says the crane count is 14. [{item['id']}]",
                      readings=[{"evidence_ref": item["id"], "passages": [CRANE]}])

    first_page = {**request("read", query="", target="D1", mode="local"),
                  "start_char": 0, "end_char": len(document.pages[0])}
    session = ResearchSession.open(
        created.metadata.session_id, store=store,
        model=Script(decision(requests=[first_page]), select, respond),
        search=no_provider, fetch=no_provider, lexical_search=no_provider)
    first = session.ask("What crane count does the document state?")
    assert first.citations[0].document_id == "D1" and CRANE in first.selected_evidence[0].content
    assert SPARE not in first.selected_evidence[0].content
    cited = first.selected_evidence[0]

    def follow(material):
        encoded = json.dumps(material["evidence"])
        assert CRANE in encoded and SPARE not in encoded
        assert material["catalog"]["documents"][0]["id"] == "D1"
        start = len(document.pages[0])
        exact = request("read", query="", target="D1", mode="local")
        exact["start_char"] = start
        exact["end_char"] = start + len(document.pages[1])
        return decision(requests=[exact])

    def select_spare(material):
        item = next(entry for entry in material["evidence"] if SPARE in entry["content"])
        assert item["page_start"] == 2
        return decision("answer", [item["id"]])

    def respond_spare(material):
        item = material["evidence"][0]
        return answer(f"The count excludes spare units. [{item['id']}]",
                      readings=[{"evidence_ref": item["id"], "passages": [SPARE]}])

    reopened = ResearchSession.open(
        created.metadata.session_id, store=SQLiteSessionStore(store.path),
        model=Script(follow, select_spare, respond_spare),
        search=no_provider, fetch=no_provider, lexical_search=no_provider)
    assert reopened.documents[0].document_id == "D1"
    assert reopened.documents[0].original_pdf == pdf
    assert reopened.turns[0].selected_evidence[0] == cited
    second = reopened.ask("What does the document exclude?")
    assert second.citations[0].document_id == "D1" and second.citations[0].page_end == 2
    assert SPARE in second.selected_evidence[0].content
    assert second.trace[-1]["budget"]["external_attempts"] == 0
    stored = SQLiteSessionStore(store.path).load(created.metadata.session_id)
    assert stored.documents[0].pages == document.pages
    assert stored.state.turns[0].selected_evidence[0] == cited
    assert stored.state.turns[1].selected_evidence[0].content == second.selected_evidence[0].content
    body = payload_of(store.path, created.metadata.session_id)
    assert body.count(SPARE) == 1 and CRANE in body
    assert pdf.hex() not in body


def _page_view(page: int, end: int | None = None) -> Evidence:
    stop = page if end is None else end
    return Evidence(
        f"D1@{page}:{stop}", "", "report.pdf", "x", "targeted_view", "D1", "D1",
        page, page + 1, "user_document", "D1", "report.pdf", page, stop, False, 0,
    )


def _labeled(pages: list[tuple[int, int]]) -> str:
    materials = tuple(_page_view(start, end) for start, end in pages)
    citation = Citation(
        1, "D1", "report.pdf", "", materials, "user_document", "D1", "report.pdf",
        min(start for start, _end in pages), max(end for _start, end in pages),
    )
    return document_page_label(citation)


def test_discontiguous_document_pages_stay_exact_after_reopen(tmp_path):
    assert _labeled([(1, 1)]) == "User-provided document · p. 1"
    assert _labeled([(1, 3)]) == "User-provided document · pp. 1\u20133"
    assert _labeled([(1, 1), (7, 7)]) == "User-provided document · pp. 1, 7"
    assert _labeled([(1, 3), (7, 7), (9, 10)]) == "User-provided document · pp. 1\u20133, 7, 9\u201310"
    assert "1\u20137" not in _labeled([(1, 1), (7, 7)])

    early = "The crane count is 14."
    late = "Returned units are excluded from the count."
    pages = [early, *[f"The cafeteria lists item {index}." for index in range(2, 7)], late]
    pdf = text_pdf(pages)
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    created = store.create()
    store.attach_document(created.metadata.session_id, 0, "yard-report.pdf", "application/pdf", pdf)
    document = store.load(created.metadata.session_id).documents[0]
    # Only these discontiguous pages are exposed. Completion must not add the
    # intervening catalog-only document text.
    reads = [{**request("read", query="", target="D1", mode="local"),
              "start_char": start, "end_char": end} for start, end in (
                  (0, len(document.pages[0])),
                  (sum(len(page) for page in document.pages[:-1]), document.text_character_count))]

    def select(material):
        chosen = [entry for entry in material["evidence"] if early in entry["content"] or late in entry["content"]]
        assert [entry["page_start"] for entry in chosen] == [1, 7]
        return decision("answer", [entry["id"] for entry in chosen])

    def respond(material):
        chosen = [entry for entry in material["evidence"] if early in entry["content"] or late in entry["content"]]
        return answer(
            f"The document states a crane count of 14. [{chosen[0]['id']}] "
            f"It excludes returned units. [{chosen[1]['id']}]",
            readings=[
                {"evidence_ref": chosen[0]["id"], "passages": [early]},
                {"evidence_ref": chosen[1]["id"], "passages": [late]},
            ],
        )

    session = ResearchSession.open(
        created.metadata.session_id, store=store,
        model=Script(decision(requests=reads), select, respond),
        search=no_provider, fetch=no_provider, lexical_search=no_provider)
    result = session.ask("What count does the document state, and what does it exclude?")
    citation = result.citations[0]
    assert citation.page_start == 1 and citation.page_end == 7
    assert len(citation.materials) == 2
    shown = render_cli(result)
    body = source_body_html(citation)
    assert "User-provided document · pp. 1, 7" in shown
    assert "User-provided document · pp. 1, 7" in body
    assert "pp. 1\u20137" not in shown and "pp. 1\u20137" not in body
    assert "Exact text from page 1." in body and "Exact text from page 7." in body

    reopened = SQLiteSessionStore(store.path).load(created.metadata.session_id)
    saved = reopened.state.turns[0].citations[0]
    assert saved.page_start == 1 and saved.page_end == 7
    assert [item.page_start for item in saved.materials] == [1, 7]
    reopened_cli = render_cli(reopened.state.turns[0])
    reopened_body = source_body_html(saved)
    assert "User-provided document · pp. 1, 7" in reopened_cli
    assert "User-provided document · pp. 1, 7" in reopened_body
    assert "pp. 1\u20137" not in reopened_cli and "pp. 1\u20137" not in reopened_body


def test_document_and_web_citations_resolve_without_a_fake_url():
    document = owned(text_pdf([BERTH]))
    view = document_text_view(document, 0, len(document.pages[0]))
    web = Evidence("E1", "https://example.test/harbor", "Harbor notice", HARBOR)
    draft = f"The document says nine meters. [{view.id}] The web source says twelve meters. [E1]"
    rendered, citations, _uses = resolve_citations(draft, [view, web], [web], [], documents=(document,))
    assert rendered.startswith("The document says nine meters. [1]")
    assert "[2]" in rendered
    assert [item.source_kind for item in citations] == ["user_document", "web"]
    assert citations[0].url == "" and citations[0].filename == "report.pdf"
    assert citations[0].page_start == citations[0].page_end == 1
    assert citations[1].url == web.url and citations[1].document_id is None
    cli = render_cli(type("Result", (), {
        "answer": rendered, "posture": "supported", "stop_reason": "supported",
        "citations": citations, "citation_uses": _uses,
    })())
    assert "User-provided document · p. 1" in cli
    assert "https://example.test/harbor" in cli
    assert "file://" not in cli and "scryraven://" not in cli
    body = source_body_html(citations[0], original_href=f"/sessions/{'ab' * 16}/documents/D1/original")
    assert BERTH in body and TEXT_ONLY_WARNING in body and "Open original PDF" in body
    assert "http://" not in body and "file://" not in body
    web_only, web_citations, _web_uses = resolve_citations("Twelve meters. [E1]", [web], [web], [])
    assert web_citations[0].url == web.url and web_citations[0].source_kind == "web"
    assert web_only.endswith("[1]")

    def choose(material):
        document_item = next(entry for entry in material["evidence"] if BERTH in entry["content"])
        web_item = next(entry for entry in material["evidence"] if HARBOR in entry["content"])
        return decision("answer", [document_item["id"], web_item["id"]])

    def respond(material):
        document_item = next(entry for entry in material["evidence"] if BERTH in entry["content"])
        web_item = next(entry for entry in material["evidence"] if HARBOR in entry["content"])
        return answer(
            f"The document says the berth clearance is nine meters. [{document_item['id']}] "
            f"The web source says the harbor depth is twelve meters. [{web_item['id']}]",
            readings=[
                {"evidence_ref": document_item["id"], "passages": [BERTH]},
                {"evidence_ref": web_item["id"], "passages": [HARBOR]},
            ],
        )

    result = run(
        "What does the document say, and what does the web source say?",
        model=Script(decision(requests=[
            request("read", query="", target="D1", mode="local"),
            request("read", query="", target="E1", mode="local"),
        ]), choose, respond),
        documents=(document,), retained_acquisitions=(web,),
        search=no_provider, fetch=no_provider, lexical_search=no_provider,
    )
    assert [item.source_kind for item in result.citations] == ["user_document", "web"]
    assert result.citations[0].url == "" and result.citations[1].url == web.url
    assert result.trace[-1]["budget"]["external_attempts"] == 0
    shown = render_cli(result)
    assert "User-provided document · p. 1" in shown and web.url in shown
    assert "file://" not in shown


def test_documents_do_not_consume_deep_or_disable_web_search(monkeypatch):
    calls = []
    production_post(monkeypatch, calls)
    document = owned(text_pdf([PAGE_FACT]))
    model = Script(
        decision(requests=[request("read", query="", target="D1", mode="local")]),
        decision(), decision("answer", ["E1"]), answer(),
    )
    result = run("What does the document say, and what is the public value?", model=model, documents=(document,))
    assert [call["json"]["type"] for call in calls] == ["deep"]
    assert calls[0]["json"]["numResults"] == 6
    timings = [event for event in result.trace if event["action"] == "acquisition_timing"]
    assert [event["kind"] for event in timings] == ["read", "search"]
    assert timings[0]["external"] is False and timings[1]["provider_search_type"] == "deep"
    assert result.posture == "supported"

    quiet = []
    production_post(monkeypatch, quiet)
    only_document = run(
        "What revenue does the document state?",
        model=Script(
            decision(requests=[request("read", query="", target="D1", mode="local")]),
            lambda material: decision("answer", [material["evidence"][0]["id"]]),
            lambda material: answer(
                f"The document says revenue was 184 million dollars. [{material['evidence'][0]['id']}]",
                readings=[{"evidence_ref": material["evidence"][0]["id"], "passages": [PAGE_FACT]}],
            ),
        ),
        documents=(document,), search=no_provider, fetch=no_provider, lexical_search=no_provider,
    )
    assert quiet == []
    assert only_document.trace[-1]["budget"]["external_attempts"] == 0
    assert only_document.citations[0].source_kind == "user_document"


def test_reading_room_upload_list_original_and_deletion(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    client = app_for(store).test_client()
    pdf = text_pdf([PAGE_FACT, ""])
    refused = client.post("/documents", data={"form_token": "missing"})
    assert refused.status_code == 415 and store.list_sessions() == ()
    forged = upload(client, "/", pdf, headers={"Origin": "https://evil.example"})
    assert forged.status_code == 403 and store.list_sessions() == ()
    page = client.get("/")
    fields = token(page, "/documents")
    replay_body = {"form_token": fields["form_token"], "pdf": (BytesIO(pdf), "annual<script>.pdf", "application/pdf")}
    created = client.post("/documents", data=replay_body)
    assert created.status_code == 303
    again = client.post("/documents", data={
        "form_token": fields["form_token"],
        "pdf": (BytesIO(pdf), "annual<script>.pdf", "application/pdf"),
    })
    assert again.status_code == 409
    metadata, = store.list_sessions()
    assert metadata.revision == 0 and metadata.title == ""
    location = f"/sessions/{metadata.session_id}"
    html = client.get(location).get_data(as_text=True)
    assert "annual&lt;script&gt;.pdf" in html and "annual<script>.pdf" not in html
    assert TEXT_ONLY_WARNING in html
    assert "1 page contained no extractable text." in html
    assert "Text-only analysis" in html
    history = client.get("/").get_data(as_text=True)
    assert "Untitled research" in history and metadata.session_id in history
    original = client.get(f"{location}/documents/D1/original")
    assert original.status_code == 200 and original.data == pdf
    assert original.mimetype == "application/pdf"
    assert original.headers["X-Content-Type-Options"] == "nosniff"
    assert original.headers["Cache-Control"] == "no-store"
    disposition = original.headers["Content-Disposition"]
    assert "filename=" in disposition and ".." not in disposition and "\r" not in disposition
    assert "<script>" not in disposition
    other = store.create()
    assert client.get(f"/sessions/{other.metadata.session_id}/documents/D1/original").status_code == 404
    assert client.get(f"{location}/documents/D2/original").status_code == 404
    assert client.get(f"/sessions/{'b' * 32}/documents/D1/original").status_code == 404
    broken = upload(client, location, b"%PDF-1.4\nnot-a-pdf", filename="broken.pdf")
    assert broken.status_code == 400
    broken_html = broken.get_data(as_text=True)
    assert "could not be read as a PDF" in broken_html
    assert "Traceback" not in broken_html and "pypdf" not in broken_html and "site-packages" not in broken_html
    assert store.load(metadata.session_id).documents[0].original_pdf == pdf
    duplicate = upload(client, location, pdf, filename="copy.pdf")
    assert duplicate.status_code == 303 and "already_attached" in duplicate.headers["Location"]
    assert ALREADY_ATTACHED_NOTICE in client.get(duplicate.headers["Location"]).get_data(as_text=True)
    assert [item.document_id for item in store.load(metadata.session_id).documents] == ["D1"]
    oversized = client.post("/ask", data={"question": "q" * (300 * 1024)})
    assert oversized.status_code == 413 and "too large" in oversized.get_data(as_text=True)
    assert "Traceback" not in oversized.get_data(as_text=True)
    multipart_question = client.post("/ask", data={"question": "q", "pdf": (BytesIO(pdf), "a.pdf")})
    assert multipart_question.status_code == 415
    confirmation = client.get(location + "/delete")
    assert "attached documents" in confirmation.get_data(as_text=True)
    deleted = client.post(location + "/delete", data=token(confirmation, location + "/delete") | {"confirm": "delete"})
    assert deleted.status_code == 303
    assert document_rows(store.path) == []
    assert store.list_sessions() == (other.metadata,)


def test_failed_first_question_keeps_the_uploaded_pdf(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")

    def explode(*_args):
        raise RuntimeError("PRIVATE_PARSER_PATH_C:/secret")

    client = app_for(store, model=explode).test_client()
    pdf = text_pdf([PAGE_FACT])
    created = upload(client, "/", pdf, filename="kept.pdf")
    assert created.status_code == 303
    metadata, = store.list_sessions()
    location = f"/sessions/{metadata.session_id}"
    failed = client.post(location + "/ask", data=token(client.get(location), location + "/ask") | {"question": "What does it say?"})
    html = failed.get_data(as_text=True)
    assert failed.status_code == 503 and "PRIVATE_PARSER" not in html
    saved = store.load(metadata.session_id)
    assert saved.metadata.revision == 0 and saved.state.turns == ()
    assert saved.documents[0].filename == "kept.pdf" and saved.documents[0].original_pdf == pdf
