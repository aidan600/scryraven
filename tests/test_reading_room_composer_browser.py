"""Offline browser checks for the integrated Reading Room composer."""

import json
from io import BytesIO
from threading import Event, Thread

import pytest
import test_citation_preview_browser as citation_browser
from pdf_fixtures import text_pdf
from PIL import Image, ImageDraw
from reading_room_samples import EARLY, QUESTION, URL, first_script, no_io, prepared_session
from test_research_loop import Script, answer, decision
from werkzeug.serving import make_server

from core.exa_transport import DiscoveryCandidate
from scryraven.reading_room import _QuietHandler, create_app
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


@pytest.fixture
def browser():
    yield from citation_browser.browser.__wrapped__()


@pytest.fixture
def citation_page(tmp_path):
    yield from citation_browser.citation_page.__wrapped__(tmp_path)


@pytest.mark.parametrize("mobile", [False, True])
def test_compact_composer_grows_without_covering_answer_and_keeps_draft(browser, citation_page, mobile):
    with citation_browser.page_at(browser, citation_page, mobile=mobile) as page:
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        footer = page.locator(".composer-footer")
        textarea = page.locator("#question")
        initial = footer.bounding_box()["height"]
        assert 65 <= initial <= 80
        assert footer.bounding_box()["y"] + initial <= page.viewport_size["height"]
        assert textarea.get_attribute("rows") == "1"
        assert page.locator(".reading-scroll").bounding_box()["height"] > page.viewport_size["height"] * .7
        textarea.fill("First line\nSecond line\nThird line\nFourth line\nFifth line")
        assert footer.bounding_box()["height"] > initial + 40
        assert footer.bounding_box()["height"] < page.viewport_size["height"] * .4
        page.goto(citation_page.rsplit("/sessions/", 1)[0])
        page.goto(citation_page)
        assert textarea.input_value() == "First line\nSecond line\nThird line\nFourth line\nFifth line"
        assert footer.bounding_box()["height"] > initial + 40
        textarea.fill(" ")
        textarea.press("Control+Enter")
        assert textarea.evaluate("el => !el.checkValidity()")
        assert not page.locator(".ask-form").get_attribute("aria-busy")
        textarea.fill("Draft after validation")
        textarea.press("Tab")
        assert page.locator(".composer-preferences summary").evaluate("el => el === document.activeElement")
        page.keyboard.press("Enter")
        assert page.locator(".preferences-menu").is_visible()
        page.keyboard.press("Escape")
        assert not page.locator(".preferences-menu").is_visible()
        assert page.locator(".composer-preferences summary").evaluate("el => el === document.activeElement")


def test_picker_drop_paste_removal_and_invalid_selection_blocks_question(browser, citation_page):
    with citation_browser.page_at(browser, citation_page) as page:
        image = {"name": "circle.png", "mimeType": "image/png", "buffer": b"not a decoded image"}
        # Client previews are provisional; the server owns decoded-content validation.
        page.locator("#attachment-files").set_input_files(image)
        assert page.locator(".attachment-chip").count() == 1
        assert page.locator(".attachment-chip img").count() == 1
        page.get_by_role("button", name="Remove circle.png").click()
        assert page.locator(".attachment-chip").count() == 0
        transfer = page.evaluate_handle("""() => {
            const transfer = new DataTransfer();
            transfer.items.add(new File(['public pdf'], 'notes.pdf', {type: 'application/pdf'}));
            return transfer;
        }""")
        page.locator(".composer").dispatch_event("dragenter", {"dataTransfer": transfer})
        assert page.locator(".composer").evaluate("el => el.classList.contains('is-dragging')")
        page.locator(".composer").dispatch_event("drop", {"dataTransfer": transfer})
        assert page.locator(".attachment-chip-name").inner_text() == "notes.pdf"
        page.locator("#question").evaluate("""el => {
            const transfer = new DataTransfer();
            transfer.items.add(new File(['clipboard image'], 'pasted.webp', {type: 'image/webp'}));
            el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: transfer, bubbles: true, cancelable: true}));
        }""")
        assert page.locator(".attachment-chip").count() == 2
        assert page.locator("#attachment-files").evaluate("el => el.files.length") == 2
        page.get_by_role("button", name="Remove pasted.webp").click()
        page.get_by_role("button", name="Remove notes.pdf").click()
        page.locator("#attachment-files").set_input_files({"name": "active.html", "mimeType": "text/html", "buffer": b"<script>1</script>"})
        assert "Only text PDFs" in page.locator(".composer-error").inner_text()
        assert page.locator(".attachment-chip-name").inner_text() == "active.html"
        page.locator("#question").fill("Keep my question and invalid attachment together")
        page.locator(".submit-question").click()
        assert not page.locator(".ask-form").get_attribute("aria-busy")
        assert page.locator("#question").input_value() == "Keep my question and invalid attachment together"
        assert page.locator("#attachment-files").evaluate("el => el.files.length") == 1
        page.get_by_role("button", name="Remove active.html").click()
        assert page.locator(".composer-error").is_hidden()


def test_scaled_narrow_layout_focus_and_source_description_precedence(browser, citation_page):
    # Narrow CSS viewport and doubled pixel density exercise zoom-sized layout and controls.
    with browser.new_context(viewport={"width": 640, "height": 500}, device_scale_factor=2) as context:
        page = context.new_page()
        page.goto(citation_page)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator("#question").focus()
        assert page.locator("#question").evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
        page.locator("a.citation").first.focus()
        preview = page.locator("#citation-preview")
        assert preview.is_visible()
        assert "tree shade" in preview.locator("h2").inner_text()
        assert preview.locator(".citation-original-title").is_visible()
        assert "field" in preview.locator(".citation-original-title").inner_text().lower()


@pytest.mark.parametrize("original_title", ["Drzewa w mieście: chłodzenie ulic", "都市の樹木と日陰"])
def test_english_explanation_precedes_original_non_english_title_and_keeps_excerpt(browser, tmp_path, original_title):
    store = SQLiteSessionStore(tmp_path / "multilingual.sqlite3")
    session = ResearchSession.create(store=store, model=Script(*first_script()), fetch=no_io,
        search=lambda _: [DiscoveryCandidate(original_title, URL, EARLY, context_kind="provider_highlights")])
    session.ask(QUESTION)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/sessions/{session.session_id}"
        with citation_browser.page_at(browser, url) as page:
            page.locator("a.citation").first.focus()
            preview = page.locator("#citation-preview")
            assert preview.is_visible()
            assert preview.locator("h2").inner_text().startswith("Explains how tree shade")
            assert preview.locator(".citation-original-title").inner_text() == original_title
            assert preview.locator("h2").bounding_box()["y"] < preview.locator(".citation-original-title").bounding_box()["y"]
            assert preview.locator(".source-url a").get_attribute("href") == URL
            preview.locator(".saved-excerpt-link").click()
            assert page.locator("#turn-1-source-1-excerpt .material-text").inner_text() == EARLY
            page.reload()
            page.locator("a.citation").first.focus()
            assert preview.locator(".citation-original-title").inner_text() == original_title
            assert preview.locator("h2").inner_text().startswith("Explains how tree shade")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_browser_research_survives_navigation_with_atomic_attachments_and_independent_turn(browser, tmp_path):
    store = SQLiteSessionStore(tmp_path / "browser-jobs.sqlite3")
    first = prepared_session(store)
    old_turns = first.turns
    second = store.create("Independent B")
    a_id, b_id = first.session_id, second.metadata.session_id
    started = {name: Event() for name in ("A", "B")}
    release = {name: Event() for name in ("A", "B")}
    calls = []

    def model(stage, prompt, material, schema):
        name = material["question"][0]
        calls.append((name, stage, material))
        if stage == "research":
            started[name].set()
            assert release[name].wait(15), "Worker barrier was never released"
            return json.dumps(decision("return"))
        if name == "A":
            assert len(material["_user_images"]) == 1
            assert material["citation_description_language"] == "pl"
            return json.dumps(answer("From your attached image: one red circle and one blue square.", support_basis="user_images"))
        assert material["citation_description_language"] == "en"
        return json.dumps(answer("Given your premises, the box holds three marbles.", support_basis="user_premises"))

    app = create_app(store=store, session_options={"model": model, "search": no_io, "fetch": no_io})
    manager = app.extensions["research_jobs"]
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    image = Image.new("RGB", (160, 100), "white")
    drawing = ImageDraw.Draw(image)
    drawing.ellipse((15, 20, 65, 70), fill="red")
    drawing.rectangle((95, 20, 145, 70), fill="blue")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pdf = text_pdf(["Synthetic public attachment for an atomic question submission."])
    try:
        with citation_browser.page_at(browser, f"{base}/sessions/{a_id}") as page:
            page.locator("#question").fill("A: What colored shapes are in this attached image?")
            page.locator(".composer-preferences summary").click()
            page.locator("#citation-language").select_option("pl")
            page.locator(".composer-preferences summary").click()
            page.locator("#attachment-files").set_input_files([
                {"name": "shapes.png", "mimeType": "image/png", "buffer": buffer.getvalue()},
                {"name": "notes.pdf", "mimeType": "application/pdf", "buffer": pdf},
            ])
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.locator(".submit-question").click()
            assert started["A"].wait(5)
            assert page.locator(".research-job").is_visible()
            assert page.locator(".research-job .turn-attachments li").count() == 2
            assert page.locator(".submit-question").is_disabled()
            a_job = manager.list(a_id)[0]
            assert a_job.state == "researching" and a_job.document_ids and a_job.image_ids
            assert store.load(a_id).state.turns == old_turns
            page.locator(f'.session-link[href="/sessions/{b_id}"]').click()
            page.wait_for_url(f"{base}/sessions/{b_id}")
            page.locator("#question").fill("B: If a box holds two marbles and I add one, how many are there?")
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.locator(".submit-question").click()
            assert started["B"].wait(5)
            assert manager.list(b_id)[0].state == "researching"
            page.goto(f"{base}/sessions/{a_id}")
            page.reload()
            assert "Researching" in page.locator(".research-job").inner_text()
            assert page.locator("#citation-language").input_value() == "pl"
            assert len(store.load(a_id).state.turns) == 3
            page.goto(f"{base}/sessions/{b_id}")
            release["A"].set()
            with manager.condition:
                assert manager.condition.wait_for(lambda: manager.get(a_job.job_id).state == "completed", timeout=10)
            notification = page.locator(".research-notifications")
            notification.get_by_role("link", name="Open conversation").wait_for(state="visible")
            assert "Research completed" in notification.inner_text()
            notification.get_by_role("link", name="Open conversation").click()
            page.wait_for_url(f"{base}/sessions/{a_id}")
            assert page.locator(".turn").count() == 4
            assert "one red circle" in page.locator("#turn-4 .answer").inner_text()
            assert page.locator("#turn-4 .turn-attachments li").count() == 2
            assert page.locator("#turn-4 .turn-attachments img").evaluate("el => el.complete && el.naturalWidth === 160")
            assert page.locator("#turn-4 a.citation").count() == 0
            pdf_link = page.locator('#turn-4 .turn-attachments a').filter(has_text="notes.pdf")
            assert page.request.get(base + pdf_link.get_attribute("href")).body() == pdf
            assert store.load(a_id).state.turns[:3] == old_turns
            assert store.load(a_id).metadata.revision == 4
            page.reload()
            assert page.locator("#turn-4 .turn-attachments img").is_visible()
            assert page.locator("#citation-language").input_value() == "pl"
            release["B"].set()
            assert manager.wait_idle(10)
            page.goto(f"{base}/sessions/{b_id}")
            assert "three marbles" in page.locator(".answer").inner_text()
            assert store.load(b_id).metadata.revision == 1
            assert [entry[:2] for entry in calls].count(("A", "research")) == 1
            assert [entry[:2] for entry in calls].count(("B", "research")) == 1
    finally:
        for event in release.values():
            event.set()
        manager.wait_idle(10)
        manager.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_uncertain_submission_then_edited_draft_requires_explicit_new_identity(browser, tmp_path):
    store = SQLiteSessionStore(tmp_path / "browser-replay.sqlite3")
    release = Event()
    calls = []

    def model(stage, prompt, material, schema):
        if stage == "research":
            calls.append(material["question"])
            assert release.wait(15)
            return json.dumps(decision("return"))
        return json.dumps(answer("Given your scenario, this is a conditional answer.", support_basis="user_premises"))

    app = create_app(store=store, session_options={"model": model, "search": no_io, "fetch": no_io})
    manager = app.extensions["research_jobs"]
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with citation_browser.page_at(browser, base) as page:
            requests = []

            def lose_first_response(route):
                requests.append(route.request)
                if len(requests) == 1:
                    accepted = route.fetch(max_redirects=0)
                    assert accepted.status == 303
                    route.abort("failed")
                else:
                    route.continue_()

            page.route("**/ask", lose_first_response)
            question = page.locator("#question")
            question.fill("First scenario: suppose a box has two marbles.")
            original_key = page.locator('[name=idempotency_key]').input_value()
            page.locator(".submit-question").click()
            page.get_by_text("Connection interrupted.", exact=False).wait_for(state="visible")
            assert len(manager.list()) == 1
            original = manager.list()[0]
            question.fill("Edited scenario: suppose a box has four marbles.")
            page.locator(".submit-question").click()
            reset = page.get_by_role("button", name="Use a new submission for this draft")
            reset.wait_for(state="visible")
            accepted_link = page.get_by_role("link", name="Open the previously accepted question")
            assert accepted_link.get_attribute("href") == f"{base}/sessions/{original.session_id}"
            assert page.locator('[name=idempotency_key]').input_value() == original_key
            assert len(manager.list()) == 1
            assert original.question == "First scenario: suppose a box has two marbles."
            reset.click()
            assert page.locator('[name=idempotency_key]').input_value() != original_key
            assert len(manager.list()) == 1  # Reset is not an implicit execution.
            assert question.input_value() == "Edited scenario: suppose a box has four marbles."
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.locator(".submit-question").click()
            assert len(manager.list()) == 2
            assert len({job.session_id for job in manager.list()}) == 2
            assert {job.question for job in manager.list()} == {
                "First scenario: suppose a box has two marbles.", "Edited scenario: suppose a box has four marbles."}
            release.set()
            assert manager.wait_idle(10)
            assert sorted(calls) == sorted(job.question for job in manager.list())
    finally:
        release.set()
        manager.wait_idle(10)
        manager.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_actual_browser_zoom_reflows_composer_and_keeps_visible_keyboard_focus(citation_page, tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    extension = tmp_path / "zoom-extension"
    extension.mkdir()
    (extension / "manifest.json").write_text(json.dumps({
        "manifest_version": 3, "name": "ScryRaven offline zoom check", "version": "1.0",
        "permissions": ["tabs"], "background": {"service_worker": "zoom.js"}}), encoding="utf-8")
    (extension / "zoom.js").write_text("chrome.runtime.onInstalled.addListener(() => {});", encoding="utf-8")
    with playwright.sync_playwright() as runtime:
        with runtime.chromium.launch_persistent_context(str(tmp_path / "browser-profile"),
                executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", headless=True,
                no_viewport=True, ignore_default_args=["--disable-extensions"], args=[
                    f"--disable-extensions-except={extension}", f"--load-extension={extension}",
                    "--window-size=1280,900"]) as context:
            page = context.new_page()
            page.goto(citation_page)
            initial_width = page.evaluate("innerWidth")
            if not context.service_workers:
                context.wait_for_event("serviceworker", timeout=5000)
            zoom = context.service_workers[0].evaluate("""async target => {
                const tabs = await chrome.tabs.query({});
                const tab = tabs.find(tab => tab.url === target);
                await chrome.tabs.setZoom(tab.id, 2);
                return await chrome.tabs.getZoom(tab.id);
            }""", page.url)
            assert zoom == 2
            page.wait_for_function("devicePixelRatio === 2")
            assert page.evaluate("innerWidth") <= initial_width / 2 + 2
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator(".sidebar").is_hidden()
            assert 65 <= page.locator(".composer-footer").bounding_box()["height"] <= 80
            assert page.locator(".composer-footer").evaluate("el => el.getBoundingClientRect().bottom <= innerHeight + 1")
            page.locator("#question").focus()
            assert page.locator("#question").evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
            page.keyboard.press("Tab")
            assert page.locator(".composer-preferences summary").evaluate("el => el === document.activeElement")
            assert page.locator(".composer-preferences summary").bounding_box()["width"] >= 44
            page.keyboard.press("Tab")
            assert page.locator(".submit-question").evaluate("el => el === document.activeElement")


def test_long_sidebar_history_does_not_push_composer_below_reading_viewport(browser, tmp_path):
    store = SQLiteSessionStore(tmp_path / "long-history.sqlite3")
    session = prepared_session(store)
    for number in range(35):
        store.create(f"Another saved conversation {number}")
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with citation_browser.page_at(browser, f"http://127.0.0.1:{server.server_port}/sessions/{session.session_id}") as page:
            assert page.locator(".session-row").count() == 36
            assert page.locator(".composer-footer").evaluate("el => el.getBoundingClientRect().bottom <= innerHeight + 1")
            assert page.locator(".reading-scroll").bounding_box()["height"] > 800
            assert page.locator(".history-list").evaluate("el => el.scrollHeight > el.clientHeight")
    finally:
        app.extensions["research_jobs"].shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
