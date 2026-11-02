"""Offline browser acceptance of per-question inference settings."""

import json
import os
from pathlib import Path
from threading import Thread

import pytest
import test_citation_preview_browser as citation_browser
from reading_room_samples import no_io, prepared_session
from werkzeug.serving import make_server

from scryraven.reading_room import _QuietHandler, create_app
from scryraven.session_store import SQLiteSessionStore


@pytest.fixture
def browser():
    yield from citation_browser.browser.__wrapped__()


@pytest.fixture
def settings_page(tmp_path):
    store = SQLiteSessionStore(tmp_path / "settings-browser.sqlite3")
    session = prepared_session(store)
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io})
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/sessions/{session.session_id}"
    finally:
        app.extensions["research_jobs"].shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def screenshot(page, name):
    destination = os.environ.get("SCRYRAVEN_REVIEW_OUTPUT")
    if destination:
        folder = Path(destination)
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / name))


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_settings_dialog_preserves_exact_ids_and_discloses_routing(browser, settings_page, width):
    with browser.new_context(viewport={"width": width, "height": 1000 if width == 1440 else 844}) as context:
        page = context.new_page()
        page.goto(settings_page)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        opening = page.get_by_role("button", name="ChatGPT plan", exact=False)
        opening.focus()
        page.keyboard.press("Enter")
        dialog = page.get_by_role("dialog", name="Run settings")
        assert dialog.is_visible()
        assert dialog.evaluate("el => el.contains(document.activeElement)")
        original = page.get_by_label("Research model identifier").input_value()
        page.get_by_label("Inference backend").select_option("openrouter")
        assert page.get_by_label("Research model identifier").input_value() == original
        assert "underlying model providers" in page.locator("#provider-disclosure").inner_text()
        assert page.get_by_label("OpenAI API processing").is_hidden()
        assert page.get_by_label("OpenAI API processing").is_disabled()
        page.get_by_label("Research model identifier").fill("openai/gpt-6.1-sol")
        page.get_by_label("Research reasoning effort").select_option("high")
        page.get_by_label("Answer model identifier").fill("openai/gpt-6.1-terra")
        page.get_by_label("Answer reasoning effort").select_option("")
        page.get_by_label("Per-run model request allowance").select_option("6")
        page.get_by_label("Use billed API inference for this question").check()
        if width < 520:
            screenshot(page, f"settings-openrouter-{width}-lower.png")
        dialog.evaluate("el => { el.scrollTop = 0; }")
        screenshot(page, f"settings-openrouter-{width}.png")
        assert dialog.evaluate("el => el.getBoundingClientRect().left >= 0 && el.getBoundingClientRect().right <= innerWidth")
        assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth")
        page.get_by_role("button", name="Use these settings").click()
        assert dialog.is_hidden()
        summary = page.locator(".run-settings-open")
        assert "OpenRouter billed" in summary.inner_text()
        assert "openai/gpt-6.1-sol · high" in summary.inner_text()
        assert "openai/gpt-6.1-terra · model default" in summary.inner_text()
        assert "Fast" not in summary.inner_text()
        assert summary.evaluate("el => el === document.activeElement")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator(".composer-footer").evaluate("el => el.getBoundingClientRect().bottom <= innerHeight + 1")
        screenshot(page, f"settings-summary-{width}.png")
        summary.click()
        page.keyboard.press("Escape")
        assert dialog.is_hidden()
        assert summary.evaluate("el => el === document.activeElement")


def test_paid_inference_requires_explicit_selection_and_fast_is_openai_only(browser, settings_page):
    with citation_browser.page_at(browser, settings_page) as page:
        page.locator(".run-settings-open").click()
        page.get_by_label("Inference backend").select_option("openai")
        assert page.get_by_label("OpenAI API processing").is_visible()
        page.get_by_label("OpenAI API processing").select_option("fast")
        assert not page.get_by_label("Use billed API inference for this question").is_checked()
        page.get_by_role("button", name="Close run settings").click()
        page.locator("#question").fill("Given that a box holds 12 apples and four are removed, how many apples remain?")
        page.locator(".submit-question").click()
        assert page.get_by_role("dialog", name="Run settings").is_visible()
        assert page.get_by_label("Use billed API inference for this question").evaluate("el => el === document.activeElement")
        assert page.locator(".ask-form").get_attribute("aria-busy") is None
        page.get_by_label("Use billed API inference for this question").check()
        page.get_by_role("button", name="Use these settings").focus()
        screenshot(page, "settings-openai-fast-desktop.png")
        page.get_by_role("button", name="Use these settings").click()
        assert "Fast" in page.locator(".run-settings-open").inner_text()
        page.locator(".run-settings-open").click()
        page.get_by_label("Inference backend").select_option("chatgpt_plan")
        assert page.get_by_label("OpenAI API processing").is_disabled()
        assert page.get_by_label("Use billed API inference for this question").is_disabled()
        assert not page.get_by_label("Use billed API inference for this question").is_checked()
        data = page.locator(".ask-form").evaluate("el => Object.fromEntries(new FormData(el))")
        assert "api_processing" not in data
        assert "paid_inference_confirmed" not in data
        assert data["backend"] == "chatgpt_plan"
        page.get_by_role("button", name="Use these settings").click()
        assert "Fast" not in page.locator(".run-settings-open").inner_text()
        assert page.locator(".run-record").first.inner_text() == "Run details"
        page.locator(".run-record summary").first.click()
        assert "Historical run configuration unknown" in page.locator(".run-record").first.inner_text()


def test_actual_200_percent_zoom_settings_dialog_and_keyboard(settings_page, tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    extension = tmp_path / "zoom-extension"
    extension.mkdir()
    (extension / "manifest.json").write_text(json.dumps({
        "manifest_version": 3, "name": "Run settings offline zoom check", "version": "1.0",
        "permissions": ["tabs"], "host_permissions": ["<all_urls>"], "background": {"service_worker": "zoom.js"}}), encoding="utf-8")
    (extension / "zoom.js").write_text("chrome.runtime.onInstalled.addListener(() => {});", encoding="utf-8")
    with playwright.sync_playwright() as runtime:
        with runtime.chromium.launch_persistent_context(str(tmp_path / "browser-profile"),
                executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", headless=True,
                no_viewport=True, ignore_default_args=["--disable-extensions"], args=[
                    f"--disable-extensions-except={extension}", f"--load-extension={extension}",
                    "--window-size=1280,900"]) as context:
            page = context.new_page()
            page.goto(settings_page)
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
            page.locator(".run-settings-open").focus()
            page.keyboard.press("Enter")
            dialog = page.get_by_role("dialog", name="Run settings")
            assert dialog.is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth")
            page.get_by_label("Answer model identifier").focus()
            assert page.get_by_label("Answer model identifier").evaluate("el => el.getBoundingClientRect().top >= 0 && el.getBoundingClientRect().bottom <= innerHeight")
            page.wait_for_timeout(150)
            if os.environ.get("SCRYRAVEN_REVIEW_OUTPUT"):
                import base64
                capture = context.service_workers[0].evaluate("""async target => {
                    const tabs = await chrome.tabs.query({});
                    const tab = tabs.find(tab => tab.url === target);
                    await chrome.tabs.update(tab.id, {active: true});
                    return await chrome.tabs.captureVisibleTab(tab.windowId, {format: 'png'});
                }""", page.url)
                (Path(os.environ["SCRYRAVEN_REVIEW_OUTPUT"]) / "settings-200-percent-zoom.png").write_bytes(base64.b64decode(capture.split(",", 1)[1]))
            page.keyboard.press("Escape")
            assert dialog.is_hidden()
            assert page.locator(".run-settings-open").evaluate("el => el === document.activeElement")



def test_completed_run_exposes_exact_snapshot_and_provider_receipt(browser, tmp_path, monkeypatch):
    from test_model_transport import Response
    from test_research_loop import answer, decision

    from scryraven.model import OpenAIModel

    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-placeholder")
    calls = []

    def post(url, **kwargs):
        payload = kwargs["json"]
        calls.append((url, payload))
        result = (decision("return") if payload["text"]["format"]["name"] == "research" else
                  answer("Given your premises, **8 apples remain**.", support_basis="user_premises"))
        return Response({"id": "offline-response", "status": "completed", "model": payload["model"],
            "service_tier": "default", "usage": {"input_tokens": 120, "output_tokens": 40,
                "input_tokens_details": {"cached_tokens": 10}, "output_tokens_details": {"reasoning_tokens": 12}},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(result)}]}]})

    store = SQLiteSessionStore(tmp_path / "completed-run.sqlite3")
    app = create_app(store=store, session_options={"model": no_io, "search": no_io, "fetch": no_io},
        run_model_factory=lambda settings: OpenAIModel(settings.model_config(), post=post, backend="api"))
    manager = app.extensions["research_jobs"]
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with citation_browser.page_at(browser, f"http://127.0.0.1:{server.server_port}") as page:
            page.locator(".run-settings-open").click()
            page.get_by_label("Inference backend").select_option("openai")
            page.get_by_label("Research model identifier").fill("gpt-6.1-sol")
            page.get_by_label("Answer model identifier").fill("gpt-6.1-terra")
            page.get_by_label("Research reasoning effort").select_option("low")
            page.get_by_label("Answer reasoning effort").select_option("")
            page.get_by_label("Per-run model request allowance").select_option("6")
            page.get_by_label("Use billed API inference for this question").check()
            page.get_by_role("button", name="Use these settings").click()
            page.locator("#question").fill("Given that a box holds 12 apples and four are removed, how many apples remain?")
            page.locator(".submit-question").click()
            page.locator(".answer").wait_for(state="visible", timeout=10000)
            assert "8 apples remain" in page.locator(".answer").inner_text()
            page.locator(".run-record summary").click()
            record = page.locator(".run-record")
            assert "gpt-6.1-sol · low" in record.inner_text()
            assert "gpt-6.1-terra · model default" in record.inner_text()
            assert "Provider-reported tokens: 120 input · 40 output" in record.inner_text()
            assert "Requested service tier: default · Returned tier: default" in record.inner_text()
            assert "Actual billing and credit balances are not available here" in record.inner_text()
            assert len(calls) == 2
            assert [payload["model"] for _, payload in calls] == ["gpt-6.1-sol", "gpt-6.1-terra"]
            screenshot(page, "settings-completed-run-receipt.png")
            page.reload()
            page.locator(".run-record summary").click()
            assert "120 input · 40 output" in record.inner_text()
            assert not page.get_by_label("Use billed API inference for this question").is_checked()
    finally:
        manager.wait_idle(5)
        manager.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_initial_mixed_api_profile_is_shown_and_requires_explicit_processing(browser, tmp_path):
    from scryraven.model import ModelConfig, ModelRole, OpenAIModel

    model = OpenAIModel(ModelConfig(ModelRole("custom-research", "max", "fast"),
                                   ModelRole("custom-answer", "low", "default")), post=no_io)
    app = create_app(database=tmp_path / "mixed-profile.sqlite3", session_options={"model": model})
    manager = app.extensions["research_jobs"]
    server = make_server("127.0.0.1", 0, app, threaded=True, request_handler=_QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with citation_browser.page_at(browser, f"http://127.0.0.1:{server.server_port}") as page:
            assert "custom-research · max" in page.locator(".run-settings-open").inner_text()
            assert "custom-answer · low" in page.locator(".run-settings-open").inner_text()
            assert "Choose processing" in page.locator(".run-settings-open").inner_text()
            page.locator(".run-settings-open").click()
            assert page.get_by_label("Research reasoning effort").input_value() == "max"
            assert page.get_by_label("OpenAI API processing").input_value() == ""
            assert "Research fast and Answer default" in page.locator(".initial-tier-profile").inner_text()
            page.get_by_label("OpenAI API processing").select_option("standard")
            page.get_by_label("Use billed API inference for this question").check()
            page.get_by_role("button", name="Use these settings").click()
            assert "Standard" in page.locator(".run-settings-open").inner_text()
            assert "Choose processing" not in page.locator(".run-settings-open").inner_text()
    finally:
        manager.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
