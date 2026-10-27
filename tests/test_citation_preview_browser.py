"""Optional offline browser checks against the real Reading Room and saved store.

Requires Playwright plus an installed Edge browser. Publication navigation is
fulfilled locally; these checks never acquire a public source or invoke a model.
"""

from contextlib import contextmanager
from pathlib import Path
from threading import Thread

import pytest
from reading_room_samples import no_io, prepared_session
from werkzeug.serving import make_server

from scryraven.reading_room import _QuietHandler, create_app
from scryraven.session_store import SQLiteSessionStore


@pytest.fixture
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    if not edge.is_file():
        pytest.skip("Optional browser checks require installed Microsoft Edge")
    with playwright.sync_playwright() as runtime:
        with runtime.chromium.launch(executable_path=str(edge), headless=True) as browser:
            yield browser


@pytest.fixture
def citation_page(tmp_path):
    store = SQLiteSessionStore(tmp_path / "preview-browser.sqlite3")
    session = prepared_session(store)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/sessions/{session.session_id}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def page_at(browser, url, *, mobile=False):
    with browser.new_context(viewport={"width": 390 if mobile else 1440, "height": 844 if mobile else 1000},
                             is_mobile=mobile, has_touch=mobile) as context:
        context.route("https://example.org/**", lambda route: route.fulfill(body="Offline original publication"))
        page = context.new_page()
        page.goto(url)
        yield page


def test_desktop_hover_persists_into_preview_and_original_opens_directly(browser, citation_page):
    with page_at(browser, citation_page) as page:
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


def test_keyboard_focus_actions_escape_and_exact_saved_excerpt(browser, citation_page):
    with page_at(browser, citation_page) as page:
        citation = page.locator('a.citation').first
        preview = page.locator('#citation-preview')
        citation.focus()
        assert preview.is_visible()
        citation.press('Tab')
        assert preview.locator('.source-url a').evaluate('(el) => el === document.activeElement')
        page.keyboard.press('Escape')
        assert preview.is_hidden()
        assert citation.evaluate('(el) => el === document.activeElement')
        page.wait_for_timeout(250)
        assert preview.is_hidden()
        citation.press('ArrowDown')
        page.keyboard.press('Tab')
        assert preview.locator('.saved-excerpt-link').evaluate('(el) => el === document.activeElement')
        page.keyboard.press('Enter')
        excerpt = page.locator('#turn-1-source-1-excerpt')
        assert excerpt.get_attribute('open') is not None
        assert excerpt.locator('summary').first.evaluate('(el) => el === document.activeElement')
        assert "Synthetic field note, initial edition." in excerpt.locator('.material-text').inner_text()
        assert "Extractive highlight" in excerpt.inner_text()
        assert preview.is_hidden()


def test_mobile_tap_exposes_preview_original_and_saved_material_without_overflow(browser, citation_page):
    with page_at(browser, citation_page, mobile=True) as page:
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
