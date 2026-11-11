"""Offline browser checks for the integrated Reading Room composer."""

import json
from io import BytesIO
from pathlib import Path
from threading import Event, Thread

import pytest
import test_citation_preview_browser as citation_browser
from pdf_fixtures import text_pdf
from PIL import Image, ImageDraw
from reading_room_samples import EARLY, QUESTION, URL, first_script, no_io, prepared_session
from test_research_loop import Script, answer, decision
from werkzeug.serving import make_server

from core.exa_transport import DiscoveryCandidate
from scryraven import dictation
from scryraven.reading_room import _QuietHandler, create_app
from scryraven.run_settings import RunSettings
from scryraven.session import ResearchSession
from scryraven.session_store import SQLiteSessionStore


@pytest.fixture
def browser():
    yield from citation_browser.browser.__wrapped__()


@pytest.fixture
def citation_page(tmp_path):
    yield from citation_browser.citation_page.__wrapped__(tmp_path)


@pytest.fixture(params=("chromium", "webkit"))
def composer_engine(request):
    yield from citation_browser.browser_at(request.param)


def test_mobile_welcome_composer_and_keyboard_viewport(composer_engine, citation_page):
    root = citation_page.rsplit("/sessions/", 1)[0]
    with composer_engine.new_context(viewport={"width": 320, "height": 720}, is_mobile=True, has_touch=True) as context:
        page = context.new_page()
        page.add_init_script("""
            const viewport = Object.assign(new EventTarget(), {height: innerHeight, offsetTop: 0, scale: 1});
            Object.defineProperty(window, 'visualViewport', {value: viewport});
            window.showKeyboard = () => {
              viewport.height = 310;
              viewport.offsetTop = 80;
              viewport.dispatchEvent(new Event('resize'));
            };
        """)
        page.goto(root)
        assert page.get_by_role("heading", name="Ask away.").is_visible()
        assert page.get_by_text("Answers grounded in public sources, with citations to explore.").is_visible()
        assert page.locator(".composer").bounding_box()["y"] > 550
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.get_by_role("link", name="Open history").click()
        page.get_by_role("button", name="Settings", exact=True).click()
        page.locator("#citation-language").select_option("ja")
        page.get_by_role("button", name="Close settings").click()
        page.reload()
        assert page.locator("#citation-language").input_value() == "ja"
        assert page.locator(".ask-form").evaluate("el => new FormData(el).get('citation_language')") == "ja"
        question = page.locator("#question")
        question.fill("This is my draft.")
        question.press("End")
        question.press("Enter")
        assert question.input_value() == "This is my draft.\n"
        page.evaluate("showKeyboard()")
        question.fill("\n".join(["A long draft line"] * 20))
        send = page.locator(".submit-question")
        assert send.evaluate("""el => {
          const {top, bottom} = el.getBoundingClientRect();
          return top >= visualViewport.offsetTop && bottom <= visualViewport.offsetTop + visualViewport.height + 1;
        }""")
        assert question.evaluate("el => el.clientHeight > 44 && el.clientHeight < el.scrollHeight")


def test_desktop_enter_respects_newlines_and_ime(composer_engine, citation_page):
    root = citation_page.rsplit("/sessions/", 1)[0]
    with citation_browser.page_at(composer_engine, root) as page:
        posts = []

        def fail_submission(route):
            posts.append(route.request.method)
            route.fulfill(status=400, body="synthetic validation error")

        page.route("**/ask", fail_submission)
        question = page.locator("#question")
        question.fill("Desktop draft")
        question.press("End")
        question.press("Shift+Enter")
        assert question.input_value() == "Desktop draft\n"
        question.dispatch_event("compositionstart")
        question.press("Enter")
        question.dispatch_event("compositionend")
        question.dispatch_event("keydown", {"key": "Enter", "keyCode": 229, "cancelable": True})
        assert posts == []
        with page.expect_response(lambda response: response.url.endswith("/ask")):
            question.press("Enter")
        assert posts == ["POST"]
        assert question.input_value().startswith("Desktop draft")


def test_dictation_uses_transient_audio_and_inserts_editable_text(composer_engine, tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "microphone.sqlite3")
    monkeypatch.setattr(dictation, "available", lambda: True)
    received = []

    def transcribe(audio):
        assert any(audio[44:])
        received.append(len(audio))
        return "What is the capital of Spain?" if len(received) == 1 else ""

    monkeypatch.setattr(dictation, "transcribe", transcribe)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    with citation_browser.running_room(app) as base, composer_engine.new_context() as context:
        page = context.new_page()
        page.add_init_script("""
            window.microphoneDenied = false;
            window.microphoneTracks = [];
            navigator.mediaDevices.getUserMedia = async () => {
              if (window.microphoneDenied) throw new DOMException('Denied', 'NotAllowedError');
              const audio = new AudioContext();
              const tone = audio.createOscillator();
              const output = audio.createMediaStreamDestination();
              tone.connect(output);
              tone.start();
              const track = output.stream.getAudioTracks()[0];
              const stop = track.stop.bind(track);
              track.stop = () => {
                stop();
                if (audio.state !== 'closed') void audio.close().catch(() => {});
              };
              window.microphoneTracks.push(track);
              await audio.resume();
              return output.stream;
            };
        """)
        page.goto(base)
        question = page.locator("#question")
        question.fill("Use official sources.")
        page.get_by_role("button", name="Start dictation").click()
        page.get_by_text("Authorize OpenAI API billing in Run Settings to use dictation.", exact=True).wait_for()
        page.locator(".run-settings-open").click()
        assert page.locator("#run-backend").input_value() == "chatgpt_plan"
        page.get_by_role("button", name="Authorize OpenAI API billed inference").click()
        page.get_by_role("button", name="Revoke OpenAI API billed inference").wait_for()
        assert page.locator("#run-backend").input_value() == "chatgpt_plan"
        page.get_by_role("button", name="Use these settings").click()

        if not page.evaluate("Boolean(window.AudioContext && window.AudioWorkletNode && window.OfflineAudioContext)"):
            # The Windows headless WebKit build has no Web Audio implementation.
            page.get_by_role("button", name="Start dictation").click()
            page.get_by_text("Microphone recording is unavailable in this browser.", exact=True).wait_for()
            assert question.input_value() == "Use official sources."
            assert received == []
            assert not store.list_sessions()
            return

        for expected in ("Transcript added to your draft.", "No speech was transcribed. Try recording again."):
            page.get_by_role("button", name="Start dictation").click()
            stop = page.get_by_role("button", name="Stop and transcribe")
            page.wait_for_function("""() => {
              const text = document.querySelector('.dictation-status').textContent;
              return text && !text.startsWith('Waiting');
            }""", timeout=23000)
            assert stop.is_visible(), page.locator(".dictation-status").inner_text()
            page.wait_for_timeout(650)
            stop.click()
            page.get_by_text(expected, exact=True).wait_for(timeout=10000)
            assert page.evaluate("microphoneTracks.every(track => track.readyState === 'ended')")
            assert question.input_value() == "Use official sources. What is the capital of Spain?"
        assert len(received) == 2

        page.get_by_role("button", name="Start dictation").click()
        page.get_by_role("button", name="Stop and transcribe").wait_for()
        page.get_by_role("button", name="Cancel dictation").click()
        page.get_by_text("Dictation canceled.", exact=True).wait_for()
        page.evaluate("microphoneDenied = true")
        page.get_by_role("button", name="Start dictation").click()
        page.get_by_text("Microphone permission was denied.", exact=False).wait_for()
        page.evaluate("microphoneDenied = false")
        page.route("**/transcribe", lambda route: route.abort())
        page.get_by_role("button", name="Start dictation").click()
        page.get_by_role("button", name="Stop and transcribe").wait_for()
        page.wait_for_timeout(650)
        page.get_by_role("button", name="Stop and transcribe").click()
        page.get_by_text("Dictation could not be completed. Try again.", exact=True).wait_for()
        page.unroute("**/transcribe")
        page.evaluate("""
            const nativeFetch = window.fetch;
            const nativeTimeout = window.setTimeout;
            window.setTimeout = (callback, delay, ...args) =>
              nativeTimeout(callback, delay === 45000 ? 250 : delay, ...args);
            window.fetch = (url, options) => String(url).endsWith('/transcribe')
              ? new Promise((resolve, reject) => options.signal.addEventListener('abort',
                  () => reject(new DOMException('Aborted', 'AbortError'))))
              : nativeFetch(url, options);
        """)
        page.get_by_role("button", name="Start dictation").click()
        page.get_by_role("button", name="Stop and transcribe").wait_for()
        page.wait_for_timeout(650)
        page.get_by_role("button", name="Stop and transcribe").click()
        page.get_by_text("Dictation timed out. Try again.", exact=True).wait_for()
        assert page.evaluate("microphoneTracks.every(track => track.readyState === 'ended')")
        assert len(received) == 2
        assert question.input_value() == "Use official sources. What is the capital of Spain?"
        assert not store.list_sessions()
        assert not app.extensions["research_jobs"].list()
        page.reload()
        assert question.input_value() == "Use official sources. What is the capital of Spain?"
        question.press("End")
        question.press("Backspace")
        assert question.input_value() == "Use official sources. What is the capital of Spain"


@pytest.mark.parametrize("mobile", [False, True])
def test_compact_composer_grows_without_covering_answer_and_keeps_draft(browser, citation_page, mobile):
    with citation_browser.page_at(browser, citation_page, mobile=mobile) as page:
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        footer = page.locator(".composer-footer")
        textarea = page.locator("#question")
        initial = footer.bounding_box()["height"]
        assert 90 <= initial <= (140 if mobile else 105)
        assert footer.bounding_box()["y"] + initial <= page.viewport_size["height"]
        if not mobile:
            assert abs(page.locator('.sidebar-foot').bounding_box()['y'] - footer.bounding_box()['y']) <= 1
        assert textarea.get_attribute("rows") == "1"
        assert page.locator(".reading-scroll").bounding_box()["height"] > page.viewport_size["height"] * .7
        textarea.fill("First line\nSecond line\nThird line\nFourth line\nFifth line")
        assert footer.bounding_box()["height"] > initial + 40
        assert footer.bounding_box()["height"] < page.viewport_size["height"] * .4
        page.locator('#attachment-files').set_input_files({"name": "notes.pdf", "mimeType": "application/pdf", "buffer": b"provisional preview"})
        assert page.locator('.attachment-chip').is_visible()
        assert footer.evaluate("el => el.getBoundingClientRect().bottom <= innerHeight + 1")
        if not mobile:
            assert abs(page.locator('.sidebar-foot').bounding_box()['y'] - footer.bounding_box()['y']) <= 1
        original_viewport = page.viewport_size
        page.set_viewport_size({"width": 320, "height": original_viewport["height"]})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert footer.evaluate("el => el.getBoundingClientRect().right <= innerWidth + 1 && el.getBoundingClientRect().bottom <= innerHeight + 1")
        assert page.locator('.submit-question').evaluate("el => el.getBoundingClientRect().right <= innerWidth + 1")
        page.set_viewport_size(original_viewport)
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
        assert page.locator(".dictation-toggle").evaluate("el => el === document.activeElement")
        page.keyboard.press("Tab")
        assert page.locator(".submit-question").evaluate("el => el === document.activeElement")


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
            page.get_by_role("button", name="Settings", exact=True).click()
            page.locator("#citation-language").select_option("pl")
            page.get_by_role("button", name="Save language").click()
            page.get_by_text("Language saved.", exact=True).wait_for()
            page.get_by_role("button", name="Close settings").click()
            page.locator("#attachment-files").set_input_files([
                {"name": "shapes.png", "mimeType": "image/png", "buffer": buffer.getvalue()},
                {"name": "notes.pdf", "mimeType": "application/pdf", "buffer": pdf},
            ])
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.locator("#question").press("Enter")
            assert started["A"].wait(5)
            assert page.locator(".research-job").is_visible()
            assert page.locator(".research-job .turn-attachments li").count() == 2
            assert page.locator(".submit-question").is_disabled()
            a_job = manager.list(a_id)[0]
            assert a_job.state == "researching" and a_job.document_ids and a_job.image_ids
            assert a_job.citation_language == "pl"
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
            a_badge = page.locator(f'.session-row[data-session-id="{a_id}"] .session-completion-state')
            assert a_badge.inner_text() == "New answer"
            assert a_badge.is_visible()
            notification.get_by_role("link", name="Open conversation").click()
            page.wait_for_url(f"{base}/sessions/{a_id}#turn-4")
            a_badge.wait_for(state="hidden")
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
            assert a_badge.is_hidden()
            assert page.locator("#turn-4 .turn-attachments img").is_visible()
            assert page.locator("#citation-language").input_value() == "pl"
            page.goto(f"{base}/sessions/{b_id}")
            assert page.locator('.research-job').is_visible()
            release["B"].set()
            assert manager.wait_idle(10)
            page.locator('.answer').wait_for(state='visible')
            assert "three marbles" in page.locator(".answer").inner_text()
            page.locator(f'.session-row[data-session-id="{b_id}"] .session-completion-state').wait_for(state="hidden")
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


def test_completion_badges_require_the_matching_answer_in_view_and_sync_between_devices(browser, tmp_path):
    store = SQLiteSessionStore(tmp_path / "completion-notifications.sqlite3")
    saved = store.create("Completion notification")
    session_id = saved.metadata.session_id

    def model(stage, prompt, material, schema):
        if stage == "research":
            return json.dumps(decision("return"))
        return json.dumps(answer("Given your premises, the result follows.\n\n" * 25,
                                 support_basis="user_premises"))

    app = create_app(store=store, session_options={"model": model, "search": no_io, "fetch": no_io})
    manager = app.extensions["research_jobs"]
    first = manager.submit("Suppose two marbles become three.", session_id=session_id,
        idempotency_key="first-completed-notification", run_settings=RunSettings.effective(model=no_io))
    assert manager.wait_idle(10)
    assert manager.get(first.job_id).state == "completed"
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with citation_browser.page_at(browser, base) as page:
            badge = page.locator(f'.session-row[data-session-id="{session_id}"] .session-completion-state')
            assert badge.inner_text() == "New answer"
            assert badge.is_visible()
            page.reload()
            assert badge.is_visible()  # Merely seeing a history row is not viewing the answer.
            page.add_init_script("""window.testDocumentHidden = true;
                Object.defineProperty(document, 'hidden', {get: () => window.testDocumentHidden});""")
            page.goto(f"{base}/sessions/{session_id}")
            assert badge.is_visible()  # A background-loaded result remains unread.
            assert not store.get_job(first.job_id).viewed
            viewed_url = f"{base}/sessions/{session_id}/jobs/{first.job_id}/viewed"
            page.route(viewed_url, lambda route: route.fulfill(status=503), times=1)
            with page.expect_response(lambda response: response.url == viewed_url and response.status == 503):
                page.evaluate("window.testDocumentHidden = false; document.dispatchEvent(new Event('visibilitychange'))")
            assert not store.get_job(first.job_id).viewed
            assert badge.is_visible()
            badge.wait_for(state="hidden")
            assert store.get_job(first.job_id).viewed

            second = manager.submit("Suppose three marbles become four.", session_id=session_id, revision=1,
                idempotency_key="second-completed-notification", run_settings=RunSettings.effective(model=no_io))
            assert manager.wait_idle(10)
            assert manager.get(second.job_id).state == "completed"
            page.wait_for_function("""jobId => document.querySelector('.session-completion-state').dataset.jobId === jobId""", arg=second.job_id)
            assert badge.is_visible()
            assert page.locator(".research-notifications a").get_attribute("href").endswith("#turn-2")
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            assert badge.is_visible()  # An older rendered answer cannot acknowledge this new job.

            with browser.new_context(viewport={"width": 900, "height": 650}) as other_device:
                other = other_device.new_page()
                other.goto(f"{base}/sessions/{session_id}")
                other_badge = other.locator(".session-completion-state")
                assert other_badge.is_visible()
                assert other.locator("#turn-2 .answer").bounding_box()["y"] > 650
                assert not store.get_job(second.job_id).viewed
                other.locator("#turn-2 .answer").evaluate("answer => answer.scrollIntoView({block: 'start'})")
                other_badge.wait_for(state="hidden")
                assert store.get_job(second.job_id).viewed
            badge.wait_for(state="hidden")  # A separate browser context's view is durable.
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            page.reload()
            assert badge.is_hidden()  # Revisiting the old document did not erase the newer acknowledgement.
            page.goto(base)
            assert badge.is_hidden()
            assert store.load(session_id).metadata.revision == 2
    finally:
        manager.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_visible_completion_stays_quiet_when_browser_storage_is_unavailable(browser, tmp_path):
    store = SQLiteSessionStore(tmp_path / "completion-no-storage.sqlite3")

    def model(stage, prompt, material, schema):
        if stage == "research":
            return json.dumps(decision("return"))
        return json.dumps(answer("Given your premises, this result is conditional.", support_basis="user_premises"))

    app = create_app(store=store, session_options={"model": model, "search": no_io, "fetch": no_io})
    manager = app.extensions["research_jobs"]
    job = manager.submit("Suppose the premise is true.", idempotency_key="storage-unavailable-completion",
        run_settings=RunSettings.effective(model=no_io))
    assert manager.wait_idle(10)
    assert manager.get(job.job_id).state == "completed"
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with browser.new_context(viewport={"width": 1440, "height": 1000}) as context:
            context.add_init_script("""Object.defineProperty(window, 'localStorage', {value: {
                getItem() { return null; }, setItem() { throw new DOMException('Unavailable', 'QuotaExceededError'); }
            }});""")
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}/sessions/{job.session_id}")
            page.locator('.session-completion-state').wait_for(state="hidden")
            page.goto(f"http://127.0.0.1:{server.server_port}")
            assert page.locator('.session-completion-state').is_hidden()
            page.goto(f"http://127.0.0.1:{server.server_port}/sessions/{job.session_id}")
            assert page.locator('.answer').is_visible()
    finally:
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
        executable = Path(runtime.chromium.executable_path)
        if not executable.is_file():
            executable = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        with runtime.chromium.launch_persistent_context(str(tmp_path / "browser-profile"),
                executable_path=str(executable), headless=True,
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
            page.wait_for_function("() => devicePixelRatio === 2")
            assert page.evaluate("innerWidth") <= initial_width / 2 + 2
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator(".sidebar").is_hidden()
            assert 90 <= page.locator(".composer-footer").bounding_box()["height"] <= 140
            assert page.locator(".composer-footer").evaluate("el => el.getBoundingClientRect().bottom <= innerHeight + 1")
            page.locator("#question").focus()
            assert page.locator("#question").evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
            page.keyboard.press("Tab")
            assert page.locator(".dictation-toggle").evaluate("el => el === document.activeElement")
            assert page.locator(".dictation-toggle").bounding_box()["width"] >= 44
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
