"""Offline V2 browser acceptance using synthetic hosted accounts and research."""

from contextlib import ExitStack
from threading import Event

import pytest
import test_hosted_browser as hosted_browser
from test_hosted_browser import EMAILS, fits, private_context, screenshot

from scryraven.run_settings import RunSettings

browser = hosted_browser.browser
hosted_ui = hosted_browser.hosted_ui


def open_settings(page, width):
    if width < 761:
        page.get_by_role("link", name="Open history", exact=True).click()
    page.get_by_role("button", name="Settings", exact=True).click()
    dialog = page.get_by_role("dialog", name="Settings", exact=True)
    assert dialog.is_visible()
    assert dialog.evaluate("el => el.contains(document.activeElement)")
    return dialog


@pytest.mark.parametrize("width", [1440, 768, 390, 320])
def test_hosted_settings_privacy_and_supported_model_controls(browser, hosted_ui, width):
    with ExitStack() as stack:
        _, admin, external, errors = private_context(stack, browser, hosted_ui, "admin", width)
        admin.goto(hosted_ui.origin)
        dialog = open_settings(admin, width)
        admin.get_by_label("Research model", exact=True).select_option("gpt-6-luna")
        admin.get_by_label("Research reasoning effort", exact=True).select_option("high")
        admin.get_by_label("Answer model", exact=True).select_option("gpt-6.1-sol")
        assert "none" not in admin.get_by_label("Answer reasoning effort", exact=True).locator("option").evaluate_all("els => els.map(el => el.value)")
        admin.get_by_label("Answer reasoning effort", exact=True).select_option("medium")
        admin.get_by_label("API processing", exact=True).select_option("fast")
        assert dialog.evaluate("el => el.scrollWidth <= el.clientWidth")
        screenshot(admin, f"preview-v2-admin-settings-{width}.png")
        admin.get_by_role("button", name="Save settings", exact=True).click()
        assert "Settings saved" in admin.locator(".notice").inner_text()
        _, tester, external_tester, errors_tester = private_context(stack, browser, hosted_ui, "alice", width)
        tester.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        assert "Fast processing" in tester.locator(".hosted-processing-note").inner_text()
        tester_dialog = open_settings(tester, width)
        assert "gpt-6-luna · High" in tester_dialog.inner_text()
        assert not tester_dialog.locator("[name=research_model], [name=answer_model], [name=backend]").count()
        tester.get_by_label("API processing", exact=True).select_option("standard")
        tester.get_by_role("button", name="Save settings", exact=True).click()
        assert tester.url.startswith(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        assert "Standard processing" in tester.locator(".hosted-processing-note").inner_text()
        if width < 761:
            tester.get_by_role("link", name="Open history", exact=True).click()
        tester.get_by_role("button", name="Privacy & participation", exact=True).click()
        privacy = tester.get_by_role("dialog", name="Privacy & participation", exact=True)
        assert "External AI and research providers process" in privacy.inner_text()
        assert "administrator can inspect conversations" in privacy.inner_text()
        assert "avoid submitting confidential information" in privacy.inner_text()
        assert privacy.evaluate("el => el.scrollWidth <= el.clientWidth")
        screenshot(tester, f"preview-v2-participation-{width}.png")
        tester.keyboard.press("Escape")
        assert privacy.is_hidden()
        if width < 761:
            assert tester.get_by_role("link", name="Open history", exact=True).evaluate("el => el === document.activeElement")
        fits(tester)
        assert external == errors == external_tester == errors_tester == []


@pytest.mark.parametrize("width", [1440, 768, 390, 320])
def test_history_layout_scrolling_menu_hit_testing_and_lifecycle(browser, hosted_ui, width):
    for index in range(32):
        hosted_ui.store.create(f"Synthetic research {index:02d}: readable long conversation title", owner_id=EMAILS["alice"])
    with ExitStack() as stack:
        _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", width)
        page.goto(hosted_ui.origin)
        mobile = width < 761
        if mobile:
            page.get_by_role("link", name="Open history", exact=True).click()
        sidebar = page.locator(".sidebar")
        assert sidebar.is_visible()
        assert sidebar.locator(".wordmark").is_visible()
        assert sidebar.locator(".new-research").bounding_box()["y"] > sidebar.locator(".wordmark").bounding_box()["y"]
        assert sidebar.locator(".sidebar-foot").bounding_box()["y"] > sidebar.locator(".new-research").bounding_box()["y"]
        assert page.locator(".history-list").evaluate("el => el.scrollHeight > el.clientHeight")
        if mobile:
            brand = sidebar.locator(".wordmark").bounding_box()
            close = sidebar.locator(".close-history").bounding_box()
            assert brand["x"] + brand["width"] < close["x"]
            assert sidebar.evaluate("el => getComputedStyle(el).flexDirection") == "column"
            sidebar.locator(".sidebar-entry").last.focus()
            page.keyboard.press("Tab")
            assert sidebar.locator(".wordmark").evaluate("el => el === document.activeElement")
            page.keyboard.press("Shift+Tab")
            assert sidebar.locator(".sidebar-entry").last.evaluate("el => el === document.activeElement")
        page.locator(".history-list").evaluate("el => { el.scrollTop = el.scrollHeight; }")
        row = page.locator(".session-row").last
        assert row.locator(".session-link-title").bounding_box()["width"] > 120
        summary = row.locator(".session-actions summary")
        before = page.url
        if mobile:
            summary.tap()
        else:
            summary.click()
        assert page.url == before
        menu = row.locator(".action-menu")
        assert menu.is_visible()
        assert menu.evaluate("el => { const r=el.getBoundingClientRect(); return r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight; }")
        screenshot(page, f"preview-v2-history-menu-{width}.png")
        page.locator(".sidebar-top").click(position={"x": 4, "y": 4})
        assert menu.is_hidden()
        summary.click()
        page.keyboard.press("Escape")
        assert menu.is_hidden()
        assert summary.evaluate("el => el === document.activeElement")
        summary.press("ArrowDown")
        assert menu.get_by_role("link", name="Rename", exact=True).evaluate("el => el === document.activeElement")
        page.keyboard.press("Enter")
        page.get_by_label("Session title", exact=True).fill("Renamed from history")
        page.get_by_role("button", name="Save", exact=True).click()
        assert page.locator("h1.session-title").inner_text() == "Renamed from history"
        if mobile:
            page.get_by_role("link", name="Open history", exact=True).click()
        current = page.locator(".session-row.selected")
        current.locator(".session-actions summary").click()
        current.get_by_role("link", name="Delete", exact=True).click()
        assert page.get_by_role("dialog", name='Delete “Renamed from history”?').is_visible()
        page.get_by_role("link", name="Cancel", exact=True).click()
        assert page.locator("h1.session-title").inner_text() == "Renamed from history"
        page.locator(".room-header .session-actions summary").click()
        page.locator(".room-header").get_by_role("link", name="Delete", exact=True).click()
        page.get_by_role("button", name="Delete session", exact=True).click()
        assert len(hosted_ui.store.list_sessions(owner_id=EMAILS["alice"])) == 32
        if mobile:
            opening = page.get_by_role("link", name="Open history", exact=True)
            opening.click()
            page.locator(".close-history").click()
            assert sidebar.is_hidden()
            opening.click()
            page.mouse.click(width - 12, 100)
            assert sidebar.is_hidden()
            opening.click()
            page.keyboard.press("Escape")
            assert sidebar.is_hidden()
            assert opening.evaluate("el => el === document.activeElement")
        fits(page)
        assert external == errors == []


def test_queued_admission_updates_to_researching_without_reload(browser, hosted_ui):
    manager = hosted_ui.app.extensions["research_jobs"]
    original_factory = manager.options_factory
    release = [Event() for _ in range(5)]
    started = [Event() for _ in range(5)]

    def factory(job):
        options = original_factory(job)
        original_model = options["model"]
        index = int(job.question.split(":", 1)[0])

        def model(stage, prompt, material, schema):
            if stage == "research":
                started[index].set()
                assert release[index].wait(20)
            return original_model(stage, prompt, material, schema)

        options["model"] = model
        return options

    manager.options_factory = factory
    try:
        with ExitStack() as stack:
            _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", 390)
            for index in range(5):
                page.goto(hosted_ui.origin)
                page.get_by_label("Your research question").fill(f"{index}: Given ten apples and two removed, how many remain?")
                page.get_by_role("button", name="Start research", exact=True).click()
                page.wait_for_url("**/sessions/**")
                if index < 4:
                    assert started[index].wait(5)
            assert not started[4].is_set()
            assert "Your question is queued." in page.locator(".job-message").inner_text()
            assert "begin automatically" in page.locator(".job-message").inner_text()
            assert "navigate away" in page.locator(".job-message").inner_text()
            assert not page.locator(".research-job .run-record").get_attribute("open")
            assert page.locator(".research-job").evaluate("el => el.querySelector('.job-message').compareDocumentPosition(el.querySelector('.run-record')) & Node.DOCUMENT_POSITION_FOLLOWING")
            page.evaluate("document.body.dataset.offlineNoReload = 'retained'")
            page.get_by_role("link", name="Open history", exact=True).click()
            assert page.locator(".session-row.selected .session-job-state").inner_text() == "Queued"
            page.locator(".close-history").click()
            screenshot(page, "preview-v2-queued-390.png")
            release[0].set()
            assert started[4].wait(5)
            page.wait_for_function("() => document.querySelector('.job-message strong').textContent === 'Researching'")
            assert page.evaluate("document.body.dataset.offlineNoReload") == "retained"
            assert page.locator(".session-row.selected .session-job-state").inner_text() == "Researching"
            screenshot(page, "preview-v2-researching-390.png")
            for event in release:
                event.set()
            assert manager.wait_idle(10)
            page.locator(".answer").wait_for(state="visible")
            record = page.locator(".turn .run-record")
            assert record.is_visible() and not record.get_attribute("open")
            assert page.locator(".turn").evaluate("el => el.querySelector('.answer').compareDocumentPosition(el.querySelector('.run-record')) & Node.DOCUMENT_POSITION_FOLLOWING")
            assert external == errors == []
    finally:
        for event in release:
            event.set()
        assert manager.wait_idle(10)


@pytest.mark.parametrize("state", ["failed", "interrupted"])
def test_unsuccessful_runs_keep_secondary_details_and_honest_status(browser, hosted_ui, state):
    job = hosted_ui.store.accept_job(
        "A synthetic saved question", idempotency_key="v2-browser-" + state,
        owner_id=EMAILS["alice"], run_settings=RunSettings.from_dict(hosted_ui.config.run_settings.to_dict()),
    )
    if state == "failed":
        hosted_ui.store.fail_job(job.job_id)
    else:
        hosted_ui.store.interrupt_jobs()
    with ExitStack() as stack:
        _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", 320)
        page.goto(hosted_ui.origin + "/sessions/" + job.session_id)
        message = page.locator(".job-message").inner_text()
        assert ("Research interrupted" if state == "interrupted" else "Research failed") in message
        assert "local server" not in message
        assert "Your question is queued" not in message
        assert page.get_by_role("button", name="Retry this question", exact=True).is_visible()
        assert page.locator(".research-job").evaluate("el => el.querySelector('.job-message').compareDocumentPosition(el.querySelector('.run-record')) & Node.DOCUMENT_POSITION_FOLLOWING")
        assert not page.locator(".run-record").get_attribute("open")
        page.locator(".run-record summary").click()
        assert "Actual billing is unknown" in page.locator(".run-record").inner_text()
        screenshot(page, f"preview-v2-{state}-320.png")
        fits(page)
        assert external == errors == []


@pytest.mark.parametrize("width", [1440, 390])
def test_modal_escape_preserves_underlying_rename_editor(browser, hosted_ui, width):
    with ExitStack() as stack:
        _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", width)
        page.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id + "?edit=rename")
        page.get_by_label("Session title", exact=True).fill("Unsaved rename stays here")
        editing_url = page.url
        settings = open_settings(page, width)
        page.keyboard.press("Escape")
        assert settings.is_hidden()
        assert page.url == editing_url
        assert page.get_by_label("Session title", exact=True).input_value() == "Unsaved rename stays here"
        if width < 761:
            page.get_by_role("link", name="Open history", exact=True).click()
        page.get_by_role("button", name="Privacy & participation", exact=True).click()
        privacy = page.get_by_role("dialog", name="Privacy & participation", exact=True)
        page.keyboard.press("Escape")
        assert privacy.is_hidden()
        assert page.url == editing_url
        assert page.get_by_label("Session title", exact=True).input_value() == "Unsaved rename stays here"
        assert external == errors == []
