"""Optional offline browser checks against the real Reading Room and saved store.

Requires Playwright and a Chromium or WebKit browser. Publication navigation is
fulfilled locally. Model and provider I/O use synthetic fixtures.
"""

from contextlib import contextmanager
from pathlib import Path
from threading import Thread

import pytest
from pdf_fixtures import text_pdf
from reading_room_samples import Script, first_script, no_io, prepared_session, source_search
from test_reading_room import submit
from test_research_loop import answer, decision
from test_research_loop import request as research_request
from werkzeug.serving import make_server

from scryraven.reading_room import _QuietHandler, create_app
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


def browser_at(name="chromium"):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        engine = getattr(runtime, name)
        try:
            launched = engine.launch()
        except playwright.Error as error:
            if "Executable doesn't exist" not in str(error):
                raise
            edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
            if name != "chromium" or not edge.is_file():
                pytest.skip(f"Optional browser checks require Playwright {name}")
            launched = engine.launch(executable_path=str(edge))
        try:
            yield launched
        finally:
            launched.close()


@pytest.fixture
def browser():
    yield from browser_at()


@pytest.fixture(params=("chromium", "webkit"))
def citation_browser(request):
    yield from browser_at(request.param)


@contextmanager
def running_room(app):
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        app.extensions["research_jobs"].shutdown()


@pytest.fixture
def citation_page(tmp_path):
    store = SQLiteSessionStore(tmp_path / "preview-browser.sqlite3")
    session = prepared_session(store)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    with running_room(app) as base:
        yield f"{base}/sessions/{session.session_id}"


@pytest.fixture
def pdf_citation_page(tmp_path):
    store = SQLiteSessionStore(tmp_path / "preview-browser.sqlite3")
    created = store.create()
    session_id = created.metadata.session_id
    store.attach_document(session_id, 0, "notes.pdf", "application/pdf",
                          text_pdf(["Synthetic cue. The crane count is 14."]))
    model = Script(
        decision(requests=[research_request("read", query="", target="D1", mode="local")]),
        lambda material: decision("return", [material["evidence"][0]["id"]]),
        lambda material: answer(f"The crane count is 14. [{material['evidence'][0]['id']}]\n\n"
                                + "More context below the citation. " * 30),
    )
    session = ResearchSession.open(session_id, store=store, model=model, search=no_io, fetch=no_io)
    session.ask("What does the synthetic document say?")
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    with running_room(app) as base:
        yield f"{base}/sessions/{session_id}"


@pytest.fixture
def completed_citation_page(tmp_path):
    store = SQLiteSessionStore(tmp_path / "preview-browser.sqlite3")
    app = create_app(store=store, session_options={"model": Script(*first_script()), "search": source_search, "fetch": no_io})
    accepted = submit(app.test_client())
    assert accepted.status_code == 303
    with running_room(app) as base:
        yield base + accepted.location.split("#")[0] + "#turn-1"


@contextmanager
def page_at(browser, url, *, mobile=False):
    with browser.new_context(viewport={"width": 390 if mobile else 1440, "height": 844 if mobile else 1000},
                             is_mobile=mobile, has_touch=mobile) as context:
        context.route("https://example.org/**", lambda route: route.fulfill(body="Offline original publication"))
        page = context.new_page()
        page.goto(url)
        yield page


def test_desktop_hover_persists_into_preview_and_original_opens_directly(citation_browser, citation_page):
    with page_at(citation_browser, citation_page) as page:
        citation = page.locator('a.citation').first
        preview = page.locator('#citation-preview')
        citation.hover()
        preview.wait_for(state="visible")
        assert "tree shade" in preview.inner_text()
        assert "example.org" in preview.inner_text()
        assert not preview.locator('.material-text').count()
        preview.hover()
        page.wait_for_timeout(250)
        assert preview.is_visible()
        assert page.locator('.workspace').bounding_box()["width"] > 1000
        with page.expect_popup() as opened:
            citation.click()
        assert opened.value.url == "https://example.org/canopy-field-notes"
        opened.value.close()
        page.locator('.question-block').first.click()
        assert preview.is_hidden()


def test_keyboard_focus_actions_escape_and_exact_saved_excerpt(citation_browser, citation_page):
    with page_at(citation_browser, citation_page) as page:
        citation = page.locator('a.citation').first
        preview = page.locator('#citation-preview')
        tab = 'Tab'
        citation.focus()
        assert preview.is_visible()
        assert citation.get_attribute("aria-expanded") == "true"
        assert citation.get_attribute("aria-controls") == "citation-preview"
        citation.press(tab)
        assert preview.locator('.source-url a').evaluate('(el) => el === document.activeElement')
        # A queued focus-scroll event can arrive after Tab enters the preview.
        page.locator('.reading-scroll').dispatch_event('scroll')
        assert preview.is_visible()
        assert preview.locator('.source-url a').evaluate('(el) => el === document.activeElement')
        page.keyboard.press('Escape')
        assert preview.is_hidden()
        assert citation.evaluate('(el) => el === document.activeElement')
        page.wait_for_timeout(250)
        assert preview.is_hidden()
        citation.press('ArrowDown')
        page.keyboard.press(tab)
        assert preview.locator('.saved-excerpt-link').evaluate('(el) => el === document.activeElement')
        page.locator('.reading-scroll').dispatch_event('scroll')
        assert preview.is_visible()
        page.keyboard.press('Enter')
        excerpt = page.locator('#turn-1-source-1-excerpt')
        assert excerpt.get_attribute('open') is not None
        assert excerpt.locator('summary').first.evaluate('(el) => el === document.activeElement')
        assert "Synthetic field note, initial edition." in excerpt.locator('.material-text').inner_text()
        assert "Extractive highlight" in excerpt.inner_text()
        assert preview.is_hidden()
        # Keeping keyboard actions stable must not leave a detached preview.
        citation.focus()
        citation.press(tab)
        assert preview.is_visible()
        page.locator('.reading-scroll').evaluate('(el) => { el.scrollTop = el.scrollHeight; }')
        page.locator('.reading-scroll').dispatch_event('scroll')
        assert preview.is_hidden()


def test_keyboard_reaches_offscreen_citations_and_keeps_preview_after_focus_scroll(citation_browser, citation_page):
    with page_at(citation_browser, citation_page) as page:
        citations = page.locator('a.citation')
        preview = page.locator('#citation-preview')
        tab = 'Tab'
        last = citations.last
        assert last.bounding_box()["y"] > page.viewport_size["height"]
        # Browser focus scroll must preserve the newly focused citation's preview.
        last.focus()
        page.wait_for_timeout(250)
        assert last.evaluate('(el) => el === document.activeElement')
        assert preview.is_visible()
        assert last.evaluate('(el) => el.getBoundingClientRect().top < innerHeight')
        page.keyboard.press('Escape')
        assert preview.is_hidden()
        # Tabbing through preview actions must also reveal each next citation,
        # including later answers that begin below the reading viewport.
        page.locator('.reading-scroll').evaluate('(el) => { el.scrollTop = 0; }')
        citations.first.focus()
        for index in range(citations.count() - 1):
            page.keyboard.press(tab)  # Original-publication action.
            page.keyboard.press(tab)  # Saved-excerpt action.
            page.keyboard.press(tab)  # Next citation in normal reading order.
            if page.locator('.sources-control').evaluate_all('(els) => els.includes(document.activeElement)'):
                page.keyboard.press(tab)  # Continue past the closed source list.
            if page.locator('.run-record > summary').evaluate_all('(els) => els.includes(document.activeElement)'):
                # Run provenance remains an inspectable keyboard stop between answers.
                record = page.locator('.run-record:has(> summary:focus)')
                assert record.locator('summary').evaluate('(el) => getComputedStyle(el).outlineStyle !== "none"')
                page.keyboard.press('Enter')
                assert record.get_attribute('open') is not None
                assert 'Historical run configuration unknown.' in record.inner_text()
                page.keyboard.press('Enter')
                assert record.get_attribute('open') is None
                page.keyboard.press(tab)
            page.wait_for_timeout(100)
            assert citations.nth(index + 1).evaluate('(el) => el === document.activeElement'), page.evaluate(
                'document.activeElement.outerHTML.slice(0, 200)')
            assert preview.is_visible()
        assert last.evaluate('(el) => el.getBoundingClientRect().top < innerHeight')
        assert page.locator('.reading-scroll').evaluate('(el) => el.scrollTop') > 0


def test_preview_reverse_tab_and_close_preserve_citation_focus(citation_browser, citation_page):
    with page_at(citation_browser, citation_page) as page:
        citation = page.locator(".citation").first
        citation.focus()
        before = reader_top(page)
        citation.press("Tab")
        page.keyboard.press("Shift+Tab")
        close = page.locator(".preview-close")
        assert close.evaluate("(el) => el === document.activeElement")
        page.keyboard.press("Shift+Tab")
        assert citation.evaluate("(el) => el === document.activeElement")
        citation.press("ArrowDown")
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Enter")
        settle_layout(page)
        assert page.locator("#citation-preview").is_hidden()
        assert citation.evaluate("(el) => el === document.activeElement")
        assert reader_top(page) == before


def test_mobile_tap_exposes_preview_original_and_saved_material_without_overflow(citation_browser, citation_page):
    with page_at(citation_browser, citation_page, mobile=True) as page:
        preview = page.locator('#citation-preview')
        page.locator('a.citation').first.tap()
        assert preview.is_visible()
        bounds = preview.bounding_box()
        assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390
        assert bounds["height"] < 600
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        with page.expect_popup() as opened:
            preview.locator('.source-url a').tap()
        assert opened.value.url == "https://example.org/canopy-field-notes"
        opened.value.close()
        preview.locator('.saved-excerpt-link').tap()
        assert page.locator('#turn-1-source-1-excerpt').get_attribute('open') is not None
        assert page.locator('#turn-1-source-1-excerpt .material-text').is_visible()
        assert preview.is_hidden()


def test_mobile_activation_without_pointerdown_opens_preview_without_fragment_navigation(citation_browser, pdf_citation_page):
    with page_at(citation_browser, pdf_citation_page, mobile=True) as page:
        citation = page.locator(".citation")
        before = reader_top(page)
        citation.dispatch_event("click", {"detail": 1})
        assert page.locator("#citation-preview").is_visible()
        settle_layout(page)
        assert reader_top(page) == before
        assert page.url == pdf_citation_page


def reader_top(page):
    return page.locator(".reading-scroll").evaluate("(reader) => reader.scrollTop")


def settle_layout(page):
    page.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


def test_short_mobile_pdf_preview_and_return_keep_the_cited_paragraph(citation_browser, pdf_citation_page):
    with citation_browser.new_context(viewport={"width": 390, "height": 430}, is_mobile=True, has_touch=True) as context:
        page = context.new_page()
        page.goto(pdf_citation_page)
        citation = page.locator(".citation").first
        citation.scroll_into_view_if_needed()
        before = reader_top(page)
        citation.tap()
        settle_layout(page)
        preview = page.locator("#citation-preview")
        assert preview.is_visible()
        assert preview.get_by_role("link", name="Open original PDF").is_visible()
        assert reader_top(page) == before
        assert page.url == pdf_citation_page
        page.locator(".reading-scroll").dispatch_event("scroll")
        assert preview.is_visible()

        preview.get_by_role("link", name="View saved excerpt").tap()
        excerpt = page.locator(".saved-excerpt")
        assert "The crane count is 14" in excerpt.locator(".material-text").inner_text()
        assert reader_top(page) > before
        excerpt.get_by_role("link", name="Back to answer").tap()
        settle_layout(page)
        assert abs(reader_top(page) - before) <= 1
        assert citation.evaluate("(el) => el === document.activeElement")
        assert preview.is_hidden()
        assert page.url == pdf_citation_page
        assert page.evaluate("scrollY") == 0


@pytest.mark.parametrize("scripts", ("disabled", "interrupted"))
def test_unavailable_script_keeps_original_pdf_and_native_sources_usable(citation_browser, pdf_citation_page, scripts):
    with citation_browser.new_context(viewport={"width": 390, "height": 430}, is_mobile=True, has_touch=True,
                                      java_script_enabled=scripts != "disabled") as context:
        if scripts == "interrupted":
            context.route("**/static/reading_room.js", lambda route: route.abort())
        context.route("**/documents/D1/original", lambda route: route.fulfill(body="Offline PDF destination"))
        page = context.new_page()
        page.goto(pdf_citation_page)
        citation = page.locator(".citation").first
        citation.scroll_into_view_if_needed()
        before = reader_top(page)
        with page.expect_popup() as opened:
            citation.tap()
        assert opened.value.url == pdf_citation_page + "/documents/D1/original"
        opened.value.close()
        assert page.url == pdf_citation_page
        assert reader_top(page) == before

        for selector in (".sources-control", ".source > summary", ".saved-excerpt > summary"):
            summary = page.locator(selector)
            summary.scroll_into_view_if_needed()
            before = reader_top(page)
            summary.tap()
            assert summary.evaluate("(el) => el.parentElement.open")
            assert abs(reader_top(page) - before) <= 1
        page.locator(".saved-excerpt .back-to-answer").tap()
        assert page.url == pdf_citation_page + "#question-1"
        assert reader_top(page) < before


@pytest.mark.parametrize("asset", ("reading_room.js", "reading_room_dictation.js"))
def test_delayed_script_does_not_scroll_away_from_open_sources(citation_browser, completed_citation_page, asset):
    with citation_browser.new_context(viewport={"width": 390, "height": 430}, is_mobile=True, has_touch=True) as context:
        pending = []
        context.route("**/static/" + asset, lambda route: pending.append(route))
        page = context.new_page()
        page.goto(completed_citation_page, wait_until="commit")
        summary = page.locator(".sources-control")
        summary.scroll_into_view_if_needed()
        summary.tap()
        assert summary.evaluate("(el) => el.parentElement.open")
        before = reader_top(page)
        assert before > 0
        assert page.evaluate("document.readyState") != "complete"
        assert len(pending) == 1

        pending.pop().continue_()
        page.wait_for_load_state()
        settle_layout(page)
        assert summary.evaluate("(el) => el.parentElement.open")
        assert abs(reader_top(page) - before) <= 1
        assert summary.evaluate("(el) => el === document.activeElement")
        assert page.url == completed_citation_page.split("#")[0]


def test_deferred_preview_opens_for_already_focused_citation(citation_browser, citation_page):
    with citation_browser.new_context() as context:
        pending = []
        context.route("**/static/reading_room.js", lambda route: pending.append(route))
        page = context.new_page()
        page.goto(citation_page, wait_until="commit")
        citation = page.locator(".citation").first
        citation.focus()
        assert page.locator("#citation-preview").is_hidden()
        assert citation.evaluate("(el) => el === document.activeElement")

        pending.pop().continue_()
        page.wait_for_load_state()
        assert page.locator("#citation-preview").is_visible()
        assert citation.evaluate("(el) => el === document.activeElement")


def test_deferred_settings_enables_dialog_and_adopts_native_history(citation_browser, citation_page):
    with citation_browser.new_context(viewport={"width": 390, "height": 600}, is_mobile=True, has_touch=True) as context:
        pending = []
        context.route("**/static/reading_room.js", lambda route: pending.append(route))
        page = context.new_page()
        page.goto(citation_page, wait_until="commit")
        page.get_by_role("link", name="Open history", exact=True).tap()
        settings = page.get_by_role("button", name="Settings", exact=True)
        assert page.url == citation_page + "#history"
        assert settings.is_disabled()

        pending.pop().continue_()
        page.wait_for_load_state()
        assert page.locator(".sidebar[aria-modal=true]").is_visible()
        assert page.locator(".history-backdrop").is_visible()
        assert settings.is_enabled()
        settings.tap()
        assert page.get_by_role("dialog", name="Settings", exact=True).is_visible()
        assert page.locator(".sidebar").is_hidden()
