"""Offline printing through the Reading Room with committed synthetic answers."""

from io import BytesIO
from urllib.parse import urljoin

import test_citation_preview_browser as citation_browser
from pypdf import PdfReader
from reading_room_samples import EARLY, Script, no_io
from test_citation_preview_browser import page_at, running_room
from test_research_loop import answer, decision

from core.exa_transport import DiscoveryCandidate
from scryraven.reading_room import create_app
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore

OTHER_QUESTION = "What was the earlier synthetic question?"
PRINT_QUESTION = "How can the synthetic canopy survey guide street design?"
PRINT_OPENING = "Synthetic canopy survey findings."
PRINT_END = "End of the synthetic survey answer."
SOURCE_URLS = ("https://example.org/canopy-survey", "https://example.org/design-notes")
TABLE_END = "Table end marker"
CODE_END = "CodeEndMarker"
browser = citation_browser.browser
pdf_citation_page = citation_browser.pdf_citation_page
saved_passage_page = citation_browser.saved_passage_page


def pdf_links(pdf):
    return [annotation for page in pdf.pages for ref in page.get('/Annots', [])
            if (annotation := ref.get_object()).get('/Subtype') == '/Link']


def make_print_fixture(database):
    """Return a real Reading Room app and path for a two-turn conversation."""
    surveys = []
    for number in range(1, 26):
        if number in (1, 9, 17):
            end = 25 if number == 17 else number + 7
            surveys.append(f"## Survey locations {number}-{end}")
        surveys.append(
            f"Survey location {number:02}. The fictional planning team records where people wait, cross the street "
            "and walk between destinations. It compares available shade at midday with shade later in the afternoon. "
            "Clear notes about time of day and pavement exposure help the team compare busy routes across the sample."
        )
    table = ("| Location | Survey method | Observation | Practical use | Notes |\n"
             "| --- | --- | --- | --- | --- |\n"
             "| Bus stop | Timed visits | Afternoon sun | Shelter placement | "
             f"{'LongSyntheticIdentifier' * 6} |\n"
             f"| Crossing | Timed visits | Open pavement | Shade at crossings | {TABLE_END} |")
    code = "```text\n" + "synthetic-location-" * 15 + CODE_END + "\n```"
    draft = "\n\n".join([f"{PRINT_OPENING} [E1]", *surveys, "## Survey records", table, code,
                         f"{PRINT_END} [E2]"])

    store = SQLiteSessionStore(database)
    session = ResearchSession.create(store=store,
        model=Script(decision("return"), answer("Earlier synthetic answer.", "unable")), search=no_io, fetch=no_io)
    session.ask(OTHER_QUESTION)
    session = ResearchSession.open(session.session_id, store=store,
        model=Script(decision(), decision("return", ["E1", "E2"]), answer(draft)),
        search=lambda query: [
            DiscoveryCandidate("Synthetic canopy survey", SOURCE_URLS[0], EARLY, context_kind="provider_highlights"),
            DiscoveryCandidate("Synthetic design notes", SOURCE_URLS[1], "Synthetic design notes for shade at bus stops.",
                               context_kind="provider_highlights"),
        ], fetch=no_io)
    session.ask(PRINT_QUESTION)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    return app, f"/sessions/{session.session_id}"


def test_print_completed_answer_spans_pages_and_preserves_source_links(browser, tmp_path):
    app, path = make_print_fixture(tmp_path / "print.sqlite3")
    with running_room(app) as base, page_at(browser, base + path) as page:
        button = page.locator('#turn-2').get_by_role('button', name='Print / Save as PDF')
        assert page.get_by_role('button', name='Print / Save as PDF').count() == 2
        assert page.locator('.print-sources').last.is_hidden()
        page_title = page.title()
        page.evaluate('''() => {
            window.printCalls = 0;
            window.print = () => { window.printCalls++; };
        }''')
        button.click()
        assert page.evaluate('window.printCalls') == 1

        pdf = PdfReader(BytesIO(page.pdf(prefer_css_page_size=True)))
        assert pdf.metadata.title == PRINT_QUESTION
        assert len(pdf.pages) >= 2
        text = " ".join(" ".join(pdf_page.extract_text().split()) for pdf_page in pdf.pages)
        assert all(content in text for content in (PRINT_QUESTION, PRINT_OPENING, TABLE_END, CODE_END, PRINT_END,
                                                    "[1]", "[2]", "Synthetic canopy survey", "Synthetic design notes"))
        assert all(f"Survey location {number:02}." in text for number in range(1, 26))
        assert all(content not in text for content in (OTHER_QUESTION, "Earlier synthetic answer.", "Reading Room",
                                                       "New research", "Run details", "Print / Save as PDF"))
        source_links = [url for link in pdf_links(pdf) if (url := link.get('/A', {}).get('/URI'))]
        assert set(source_links) == set(SOURCE_URLS)
        assert all(source_links.count(url) >= 2 for url in SOURCE_URLS)  # Inline and in Sources.
        assert not page.locator('.turn.is-printing').count()
        assert page.title() == page_title
        assert button.is_visible()


def test_native_print_reroutes_saved_passage_link_and_restores_it(browser, saved_passage_page):
    with page_at(browser, saved_passage_page) as page:
        citation = page.locator('a.citation').first
        original_href = citation.get_attribute('href')
        assert '-passage-' in original_href

        pdf = PdfReader(BytesIO(page.pdf(prefer_css_page_size=True)))
        annotations = pdf_links(pdf)
        targets = {(link.get('/Dest') or '').lstrip('/') for link in annotations}
        assert 'print-turn-1-source-1' in targets
        assert any(name.lstrip('/') == 'print-turn-1-source-1' for name in pdf.named_destinations)
        assert any(annotation.get('/A', {}).get('/URI') == 'https://example.org/record' for annotation in annotations)

        assert citation.get_attribute('href') == original_href
        assert page.locator('.sources-overview').is_visible()


def test_print_pdf_citation_preserves_protected_link_and_page_locator(browser, pdf_citation_page):
    with page_at(browser, pdf_citation_page) as page:
        original_href = page.locator('.sources-overview .source-preview .source-url a').get_attribute('href')
        pdf = PdfReader(BytesIO(page.pdf(prefer_css_page_size=True)))
        text = ' '.join(pdf_page.extract_text() for pdf_page in pdf.pages)
        assert 'notes.pdf' in text
        assert 'p. 1' in text
        source_links = [link.get('/A', {}).get('/URI') for link in pdf_links(pdf)]
        assert source_links.count(urljoin(page.url, original_href)) >= 2


def test_empty_reading_room_has_no_answer_print_ui(tmp_path):
    app = create_app(database=tmp_path / 'empty.sqlite3', session_options={"model": no_io, "search": no_io, "fetch": no_io})
    markup = app.test_client().get('/').get_data(as_text=True)
    assert 'print-sources' not in markup
    assert 'Print / Save as PDF' not in markup
