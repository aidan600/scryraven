"""App-generated answer downloads: real PDF bytes, no browser dependency."""

import re
import unicodedata
from contextlib import contextmanager
from io import BytesIO
from urllib.parse import urlsplit
from urllib.request import OpenerDirector

import pytest
import test_hosted_reading_room as hosted_http
from pdf_fixtures import text_pdf
from pypdf import PdfReader
from reading_room_samples import Script, no_io
from table_read_samples import (
    HEADERS,
    LAST_CELL_MARKER,
    LAST_CELL_URL,
    QUESTION,
    ROWS,
    SOURCE_TITLE,
    SOURCE_URL,
    make_table_fixture,
)
from test_research_loop import answer, decision
from test_research_loop import request as research_request
from werkzeug.http import parse_options_header

from scryraven import answer_pdf
from scryraven.reading_room import create_app
from scryraven.results import CompletedAnswer, resolve_citations
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore
from scryraven.sources import Evidence

key = hosted_http.key
config = hosted_http.config
hosted_room = hosted_http.room


@pytest.fixture
def renderer():
    if not answer_pdf.available():
        pytest.skip("App-generated PDF checks require the optional PDF renderer and native libraries")


@contextmanager
def table_room(tmp_path):
    database = tmp_path / "download.sqlite3"
    app, path = make_table_fixture(database)
    try:
        yield app, path, SQLiteSessionStore(database)
    finally:
        app.extensions["research_jobs"].shutdown()


def pdf_text(pdf):
    extracted = " ".join(page.extract_text() for page in pdf.pages)
    extracted = re.sub(r"(?<=\w)-\s+(?=\w)", "-", extracted)
    extracted = re.sub(r"\s+([,.;:!?])", r"\1", extracted)
    return unicodedata.normalize("NFC", " ".join(extracted.split()))


def plain_cell(text):
    return text.replace("**", "").replace("*", "").replace("`", "").replace("[E1]", "[1]")


def annotations(pdf):
    return [item for page in pdf.pages for reference in page.get("/Annots", ())
            if (item := reference.get_object()).get("/Subtype") == "/Link"]


def uris(pdf):
    return [item["/A"]["/URI"] for item in annotations(pdf) if item.get("/A", {}).get("/S") == "/URI"]


def internal_target_page(pdf, link):
    target = link.get("/Dest") or link.get("/A", {}).get("/D")
    if isinstance(target, str):
        destination = pdf.named_destinations.get(target.lstrip("/")) or pdf.named_destinations.get(target)
        assert destination is not None, f"Unresolved internal PDF destination: {target}"
        return pdf.get_destination_page_number(destination)
    if target:
        reference = target[0]
        return next(index for index, page in enumerate(pdf.pages) if page.indirect_reference == reference)
    return None


def assert_download(response, turn=1):
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    disposition, options = parse_options_header(response.headers["Content-Disposition"])
    assert disposition == "attachment" and options["filename"] == f"scryraven-answer-{turn}.pdf"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.data.startswith(b"%PDF-")
    return PdfReader(BytesIO(response.data))


@pytest.mark.parametrize("ready", (True, False))
def test_download_action_and_native_print_are_distinct_and_follow_renderer_availability(tmp_path, monkeypatch, ready):
    monkeypatch.setattr(answer_pdf, "available", lambda: ready)
    with table_room(tmp_path) as (app, path, _):
        client = app.test_client()
        for route in (path, path + "/turns/1/print"):
            response = client.get(route)
            assert response.status_code == 200
            assert ("Download PDF" in response.text) == ready
            assert (f'href="{path}/turns/1/pdf"' in response.text) == ready
            assert "Print" in response.text


def test_unavailable_download_is_explicit_and_does_not_hold_the_render_slot(tmp_path, monkeypatch):
    with table_room(tmp_path) as (app, path, store):
        session_id = path.rsplit("/", 1)[1]
        before = store.load(session_id)
        monkeypatch.setattr(answer_pdf, "available", lambda: False)

        def unavailable(*args, **kwargs):
            raise answer_pdf.PdfUnavailable()

        monkeypatch.setattr(answer_pdf, "render_pdf", unavailable)
        response = app.test_client().get(path + "/turns/1/pdf")
        assert response.status_code == 503 and response.mimetype == "text/plain"
        assert "unavailable" in response.text and "Print" in response.text
        assert QUESTION not in response.text and LAST_CELL_MARKER not in response.text
        assert response.headers["Cache-Control"] == "no-store"
        monkeypatch.setattr(answer_pdf, "render_pdf", lambda *args, **kwargs: b"%PDF-synthetic-mocked-response")
        retry = app.test_client().get(path + "/turns/1/pdf")
        assert retry.status_code == 200 and retry.mimetype == "application/pdf"
        assert store.load(session_id) == before and not store.list_jobs()


def test_download_uses_existing_identity_ownership_host_and_turn_boundaries(hosted_room, config, key, monkeypatch):
    app, store, alice, bob = hosted_room
    path = f"/sessions/{alice}/turns/1/pdf"
    before = store.load(alice)
    calls = []

    def controlled_render(markup, *, base_url):
        calls.append((markup, base_url))
        return b"%PDF-synthetic-mocked-response"

    monkeypatch.setattr(answer_pdf, "render_pdf", controlled_render)
    monkeypatch.setattr(answer_pdf, "available", lambda: True)
    for email in ("alice@example.test", config.admin_email):
        response = hosted_http.get(hosted_room, config, key, path, email=email)
        assert response.status_code == 200 and response.mimetype == "application/pdf"
        assert response.headers["Cache-Control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["Referrer-Policy"] == "same-origin"
    assert len(calls) == 2 and all(origin == config.origin for _, origin in calls)
    assert all("the standard specifies 12 kPa" in markup for markup, _ in calls)
    assert app.test_client().get(path, base_url=config.origin).status_code == 401
    assert app.test_client().get(path, base_url=config.origin,
                                 headers={"Cf-Access-Jwt-Assertion": "invalid"}).status_code == 401
    assert hosted_http.get(hosted_room, config, key, path, email="bob@example.test").status_code == 404
    assert app.test_client().get(path, base_url="https://foreign.example.test",
                                 headers=hosted_http.headers(config, key)).status_code == 400
    for index in (0, 2, 999999):
        assert hosted_http.get(hosted_room, config, key, f"/sessions/{alice}/turns/{index}/pdf").status_code == 404
    assert hosted_http.get(hosted_room, config, key, f"/sessions/{bob}/turns/1/pdf",
                           email="bob@example.test").status_code == 404
    assert len(calls) == 2
    assert store.load(alice) == before and not store.list_jobs()


def test_busy_download_is_not_queued_and_releases_the_slot_after_completion(tmp_path, monkeypatch):
    with table_room(tmp_path) as (app, path, store):
        calls = []
        busy = []

        def controlled_render(markup, *, base_url):
            calls.append(markup)
            busy.append(app.test_client().get(path + "/turns/1/pdf"))
            return b"%PDF-synthetic-mocked-response"

        monkeypatch.setattr(answer_pdf, "render_pdf", controlled_render)
        first = app.test_client().get(path + "/turns/1/pdf")
        assert first.status_code == 200 and len(calls) == len(busy) == 1
        assert busy[0].status_code == 503 and busy[0].headers["Retry-After"] == "3"
        assert busy[0].headers["Cache-Control"] == "no-store"
        assert QUESTION not in busy[0].text
        retry = app.test_client().get(path + "/turns/1/pdf")
        assert retry.status_code == 200 and len(calls) == len(busy) == 2
        assert not store.list_jobs()


def test_real_download_keeps_complete_selectable_grid_text_and_live_link_destinations(renderer, tmp_path):
    with table_room(tmp_path) as (app, path, store):
        session_id = path.rsplit("/", 1)[1]
        before = store.load(session_id)
        response = app.test_client().get(path + "/turns/1/pdf")
        pdf = assert_download(response)
        text = pdf_text(pdf)
        assert QUESTION in text
        assert all(header in text for header in HEADERS)
        layout = pdf.pages[0].extract_text(extraction_mode="layout")
        header_line = next(line for line in layout.splitlines() if all(header in line for header in HEADERS))
        assert re.search(r"\s{2,}".join(re.escape(header) for header in HEADERS), header_line)
        assert all(" ".join(plain_cell(cell).split()) in text for row in ROWS for cell in row)
        assert text.count(LAST_CELL_MARKER) == 1
        assert "Download PDF" not in text and "Back to answer" not in text and "More columns" not in text
        assert uris(pdf).count(LAST_CELL_URL) == 1
        assert uris(pdf).count(SOURCE_URL) == 1
        targets = [internal_target_page(pdf, link) for link in annotations(pdf)
                   if link.get("/Dest") or link.get("/A", {}).get("/S") == "/GoTo"]
        source_pages = {index for index, page in enumerate(pdf.pages) if SOURCE_TITLE in page.extract_text()}
        assert targets and all(target in source_pages for target in targets)
        assert all(target is not None and 0 <= target < len(pdf.pages) for target in targets)
        assert store.load(session_id) == before and not store.list_jobs()
        head = app.test_client().head(path + "/turns/1/pdf")
        assert head.status_code == 200 and head.mimetype == "application/pdf" and head.data == b""
        assert head.headers["Content-Disposition"] == response.headers["Content-Disposition"]


def test_tall_table_row_paginates_without_losing_unicode_or_the_terminal_cell(renderer, tmp_path):
    evidence = Evidence("E1", SOURCE_URL, SOURCE_TITLE, "Synthetic source for a long table only.")
    parts = [f"TallRowPart{index:03} preserves the complete synthetic observation." for index in range(80)]
    terminal = "Terminal café crème brûlée observation."
    draft = ("| Sample | Complete observation | Final note |\n| --- | --- | --- |\n"
             "| Fromage affiné | " + " ".join(parts) + " [E1] | "
             + terminal + f" {LAST_CELL_MARKER} |")
    prose, citations, uses = resolve_citations(draft, [evidence], [evidence], [])
    prose = prose.replace(LAST_CELL_MARKER, f"[{LAST_CELL_MARKER}]({LAST_CELL_URL})")
    result = CompletedAnswer(prose, "supported", "supported", (evidence,), (), (evidence,), citations, uses)
    store = SQLiteSessionStore(tmp_path / "tall-row.sqlite3")
    session = ResearchSession.create(store=store, engine=lambda question, **kwargs: result,
                                     model=no_io, search=no_io, fetch=no_io)
    session.ask("Keep every word of the synthetic café comparison.")
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    try:
        pdf = assert_download(app.test_client().get(f"/sessions/{session.session_id}/turns/1/pdf"))
        assert len(pdf.pages) >= 2
        text = pdf_text(pdf)
        assert "Fromage affiné" in text and terminal in text
        # A repeated column header can interrupt extracted cell prose at a
        # page boundary; every original observation must still be present once.
        body_text = " ".join(text.replace("Sample Complete observation Final note", "").split())
        assert all(body_text.count(part) == 1 for part in parts)
        assert text.count(LAST_CELL_MARKER) == 1 and uris(pdf).count(LAST_CELL_URL) == 1
    finally:
        app.extensions["research_jobs"].shutdown()


def test_downloaded_private_document_link_keeps_https_locator_and_attachment_authorization(
    renderer, hosted_room, config, key,
):
    app, store, _, _ = hosted_room
    created = store.create("Synthetic private café source", owner_id="alice@example.test")
    sid = created.metadata.session_id
    original = text_pdf(["Synthetic first page.", "The synthetic second page records fourteen cranes."])
    store.attach_document(sid, 0, "café-notes.pdf", "application/pdf", original)
    model = Script(
        decision(requests=[research_request("read", query="", target="D1", mode="local")]),
        lambda material: decision("return", [item["id"] for item in material["evidence"]]),
        answer("The attached café notes record fourteen cranes. [D1]"),
    )
    session = ResearchSession.open(sid, store=store, model=model, search=no_io, fetch=no_io)
    session.ask("What do the private synthetic notes state?")
    response = hosted_http.get(hosted_room, config, key, f"/sessions/{sid}/turns/1/pdf")
    pdf = assert_download(response)
    text = pdf_text(pdf)
    assert "café-notes.pdf" in text
    assert "pp. 1–2" in text or "pp. 1-2" in text
    original_url = config.origin + f"/sessions/{sid}/documents/D1/original"
    assert original_url in uris(pdf)
    parsed = urlsplit(original_url)
    assert parsed.scheme == "https" and parsed.netloc == urlsplit(config.origin).netloc
    assert app.test_client().get(parsed.path, base_url=config.origin).status_code == 401
    assert hosted_http.get(hosted_room, config, key, parsed.path, email="bob@example.test").status_code == 404
    assert hosted_http.get(hosted_room, config, key, parsed.path).data == original
    assert hosted_http.get(hosted_room, config, key, parsed.path, email=config.admin_email).data == original


def test_renderer_refuses_a_synthetic_external_image_before_network_opening(renderer, monkeypatch):
    openings = []

    def forbidden_open(self, request, *args, **kwargs):
        openings.append(request)
        raise AssertionError("The PDF renderer must not open an external resource")

    monkeypatch.setattr(OpenerDirector, "open", forbidden_open)
    with pytest.raises(answer_pdf.PdfUnavailable):
        answer_pdf.render_pdf(
            '<p>Synthetic image-resource check.</p><img src="https://example.org/synthetic-pdf-image.png" alt="Synthetic">',
            base_url="https://example.org/",
        )
    assert openings == []
