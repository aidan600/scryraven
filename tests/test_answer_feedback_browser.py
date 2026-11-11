"""Hosted answer feedback through the ordinary browser and durable HTTP path."""

from contextlib import ExitStack
from threading import Event

import pytest
import test_hosted_browser as hosted_browser
from pdf_fixtures import text_pdf
from test_hosted_browser import fits, private_context, screenshot

browser = hosted_browser.browser
hosted_ui = hosted_browser.hosted_ui


def feedback_is_open(section):
    return section.locator("summary").evaluate("el => el.closest('details').open")


def open_feedback(section):
    if not feedback_is_open(section):
        section.locator("summary").click()
    assert feedback_is_open(section)


def send_feedback(page, turn_index, text):
    section = page.locator(f"#feedback-{turn_index}")
    open_feedback(section)
    section.locator("textarea").fill(text)
    section.get_by_role("button", name="Send feedback", exact=True).click()
    page.wait_for_function(
        "([index, text]) => document.querySelector('#feedback-' + index + ' .feedback-comments li:last-child .feedback-text')?.textContent === text",
        arg=[turn_index, text],
    )
    assert section.locator("textarea").input_value() == ""
    assert feedback_is_open(section)
    assert section.locator(".feedback-confirmation").is_visible()


@pytest.mark.parametrize("width", [1440, 390, 320])
def test_feedback_is_quiet_durable_answer_specific_and_keeps_followup_draft(browser, hosted_ui, width):
    with ExitStack() as stack:
        _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", width)
        page.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        assert page.locator(".answer-feedback").count() == 3
        for section in page.locator(".answer-feedback").all():
            assert not feedback_is_open(section)
            assert section.locator("summary").is_visible()
            assert not section.locator("textarea").is_visible()
            assert not section.get_by_role("button", name="Send feedback", exact=True).is_visible()
            assert not section.locator(".feedback-comments").is_visible()
        first = page.locator("#feedback-1")
        first.scroll_into_view_if_needed()
        screenshot(page, f"feedback-collapsed-{width}.png")
        first.locator("summary").focus()
        page.keyboard.press("Enter")
        assert feedback_is_open(first)
        assert first.locator("textarea").is_visible()
        first.locator("summary").focus()
        page.keyboard.press("Space")
        assert not feedback_is_open(first)
        assert not first.locator("textarea").is_visible()
        open_feedback(first)
        first.scroll_into_view_if_needed()
        screenshot(page, f"feedback-expanded-{width}.png")
        assert page.locator("#turn-1").evaluate(
            "el => !!(el.querySelector('.sources-overview').compareDocumentPosition(el.querySelector('.answer-feedback')) & Node.DOCUMENT_POSITION_FOLLOWING)"
        )
        revision = hosted_ui.store.load(hosted_ui.alice_id).metadata.revision
        page.locator("#question").fill("A separate follow-up draft")
        page.locator("#attachment-files").set_input_files({
            "name": "follow-up.pdf", "mimeType": "application/pdf", "buffer": text_pdf(["Separate draft attachment"]),
        })
        page.evaluate("document.body.dataset.feedbackSentinel = 'same document'")
        literal = '<script>window.feedbackExecuted = true</script>\nThe first answer needs a qualification.'
        send_feedback(page, 1, literal)
        assert page.evaluate("window.feedbackExecuted") is None
        assert page.locator(".answer-feedback script").count() == 0
        assert page.locator("#question").input_value() == "A separate follow-up draft"
        assert page.locator(".attachment-chip-name").inner_text() == "follow-up.pdf"
        assert page.evaluate("document.body.dataset.feedbackSentinel") == "same document"
        send_feedback(page, 1, "A second comment on the first answer.")
        send_feedback(page, 2, "This belongs to the humidity answer.")
        assert page.locator("#feedback-1 .feedback-text").all_text_contents() == [literal, "A second comment on the first answer."]
        assert page.locator("#feedback-2 .feedback-text").all_text_contents() == ["This belongs to the humidity answer."]
        assert page.locator("#feedback-3 .feedback-text").count() == 0
        assert "2" in page.locator("#feedback-1 summary").inner_text()
        assert "1" in page.locator("#feedback-2 summary").inner_text()
        assert hosted_ui.store.load(hosted_ui.alice_id).metadata.revision == revision
        fits(page)
        assert page.locator("#feedback-2").evaluate("el => el.scrollWidth <= el.clientWidth")
        screenshot(page, f"answer-feedback-owner-{width}.png")
        page.reload()
        for section in page.locator(".answer-feedback").all():
            assert not feedback_is_open(section)
            assert not section.locator(".feedback-comments").is_visible()
        assert page.locator("#feedback-1 .feedback-text").all_text_contents() == [literal, "A second comment on the first answer."]
        assert page.locator("#feedback-2 .feedback-text").all_text_contents() == ["This belongs to the humidity answer."]
        open_feedback(page.locator("#feedback-1"))
        page.locator("#feedback-text-1").fill("An unsent additional comment")
        page.locator("#feedback-1 .feedback-remove").first.focus()
        page.keyboard.press("Enter")
        page.wait_for_function("() => document.querySelectorAll('#feedback-1 .feedback-text').length === 1")
        assert page.locator("#feedback-1 .feedback-text").inner_text() == "A second comment on the first answer."
        assert page.locator("#feedback-text-1").input_value() == "An unsent additional comment"
        assert page.locator("#feedback-text-1").evaluate("el => el === document.activeElement")
        assert feedback_is_open(page.locator("#feedback-1"))
        assert page.locator("#feedback-1 .feedback-confirmation").is_visible()
        _, admin, external_admin, errors_admin = private_context(stack, browser, hosted_ui, "admin", width)
        admin.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        assert not feedback_is_open(admin.locator("#feedback-1"))
        open_feedback(admin.locator("#feedback-1"))
        open_feedback(admin.locator("#feedback-2"))
        assert admin.locator("#feedback-1 .feedback-text").inner_text() == "A second comment on the first answer."
        assert admin.locator("#feedback-2 .feedback-text").inner_text() == "This belongs to the humidity answer."
        assert admin.locator(".answer-feedback form, .answer-feedback textarea").count() == 0
        fits(admin)
        admin.locator("#feedback-1").scroll_into_view_if_needed()
        screenshot(admin, f"answer-feedback-admin-{width}.png")
        assert external == errors == external_admin == errors_admin == []


def test_feedback_works_during_research_and_completion_does_not_discard_comment(browser, hosted_ui):
    manager = hosted_ui.app.extensions["research_jobs"]
    original_factory = manager.options_factory
    started, release = Event(), Event()

    def factory(job):
        options = original_factory(job)
        original_model = options["model"]

        def model(stage, prompt, material, schema):
            if stage == "research":
                started.set()
                assert release.wait(20)
            return original_model(stage, prompt, material, schema)

        options["model"] = model
        return options

    manager.options_factory = factory
    try:
        with ExitStack() as stack:
            _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", 390)
            page.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
            page.get_by_label("Ask a follow-up", exact=True).fill("Given ten apples and two removed, how many remain?")
            page.get_by_role("button", name="Ask follow-up", exact=True).click()
            assert started.wait(5)
            page.locator("#research-status").wait_for()
            page.wait_for_load_state("domcontentloaded")
            send_feedback(page, 1, "A comment while my next question is researching.")
            assert page.locator(".answer").count() == 3
            assert page.locator(".submit-question").is_disabled()
            open_feedback(page.locator("#feedback-2"))
            page.locator("#feedback-text-2").fill("An unsent comment stays here through completion.")
            page.locator("#feedback-2 summary").click()
            assert not feedback_is_open(page.locator("#feedback-2"))
            page.locator("#question").fill("A later question draft stays separate.")
            page.evaluate("document.body.dataset.feedbackSentinel = 'research page retained'")
            release.set()
            assert manager.wait_idle(10)
            page.locator(".research-notifications a").wait_for(state="visible")
            assert page.evaluate("document.body.dataset.feedbackSentinel") == "research page retained"
            assert page.locator("#feedback-text-2").input_value() == "An unsent comment stays here through completion."
            assert page.locator("#question").input_value() == "A later question draft stays separate."
            send_feedback(page, 2, "An unsent comment stays here through completion.")
            assert page.locator("#feedback-1 .feedback-text").inner_text() == "A comment while my next question is researching."
            with page.expect_response(lambda response: response.request.is_navigation_request()):
                page.locator(".research-notifications a").click()
            page.wait_for_load_state("domcontentloaded")
            assert page.url.endswith("#turn-4")
            assert page.locator(".answer").count() == 4
            assert not feedback_is_open(page.locator("#feedback-2"))
            open_feedback(page.locator("#feedback-2"))
            assert page.locator("#feedback-2 .feedback-text").inner_text() == "An unsent comment stays here through completion."
            assert page.locator("#feedback-4 .feedback-text").count() == 0
            assert page.locator("#question").input_value() == "A later question draft stays separate."
            fits(page)
            assert external == errors == []
    finally:
        release.set()
        assert manager.wait_idle(10)


def test_feedback_native_forms_work_without_javascript(browser, hosted_ui):
    with browser.new_context(viewport={"width": 1440, "height": 1000}, java_script_enabled=False,
                             extra_http_headers={"Cf-Access-Jwt-Assertion": "alice"},
                             ignore_https_errors=True) as context:
        external = []

        def loopback_only(route):
            if not route.request.url.startswith(hosted_ui.origin + "/"):
                external.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        context.route("**/*", loopback_only)
        page = context.new_page()
        page.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        assert not feedback_is_open(page.locator("#feedback-1"))
        open_feedback(page.locator("#feedback-1"))
        page.locator("#feedback-text-1").fill("A native form comment.")
        page.locator("#feedback-1").get_by_role("button", name="Send feedback", exact=True).click()
        page.wait_for_url("**#feedback-1")
        assert feedback_is_open(page.locator("#feedback-1"))
        assert page.locator("#feedback-1 .feedback-confirmation").is_visible()
        assert page.locator("#feedback-1 .feedback-text").inner_text() == "A native form comment."
        page.reload()
        assert page.locator("#feedback-1 .feedback-text").inner_text() == "A native form comment."
        with page.expect_navigation():
            page.locator("#feedback-1 .feedback-remove").click()
        assert page.locator("#feedback-1 .feedback-text").count() == 0
        assert feedback_is_open(page.locator("#feedback-1"))
        assert page.locator("#feedback-1 .feedback-confirmation").is_visible()
        assert external == []


def test_invalid_feedback_stays_open_and_retains_text(browser, hosted_ui):
    with ExitStack() as stack:
        _, page, external, errors = private_context(stack, browser, hosted_ui, "alice", 390)
        page.goto(hosted_ui.origin + "/sessions/" + hosted_ui.alice_id)
        section = page.locator("#feedback-1")
        open_feedback(section)
        section.locator("textarea").fill("   ")
        section.get_by_role("button", name="Send feedback", exact=True).click()
        section.locator(".feedback-error").wait_for(state="visible")
        assert feedback_is_open(section)
        assert section.locator("textarea").input_value() == "   "
        assert section.locator("textarea").evaluate("el => el === document.activeElement")
        assert external == errors == []
