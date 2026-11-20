"""Optional standalone-PDF UX checks; native iPhone sharing remains a device check."""

import base64
import hashlib
import re
from contextlib import contextmanager
from io import BytesIO

import pytest
import test_citation_preview_browser as citation_browser
from pypdf import PdfReader
from table_read_samples import LAST_CELL_MARKER, LAST_CELL_URL, SOURCE_URL, make_table_fixture
from test_answer_pdf import pdf_text, uris
from test_citation_preview_browser import running_room

from scryraven import answer_pdf

pdf_browser = citation_browser.citation_browser


@pytest.fixture
def renderer():
    if not answer_pdf.available():
        pytest.skip("Standalone PDF checks require the optional PDF renderer and native libraries")


def settle(page):
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


def setup_script(mode="navigator", share="success", downloads=True):
    standalone = ""
    if mode == "navigator":
        standalone = "Object.defineProperty(navigator, 'standalone', {value: true, configurable: true});"
    elif mode == "display":
        standalone = """
            const browserMedia = window.matchMedia.bind(window);
            window.matchMedia = query => {
                const result = browserMedia(query);
                if (query === '(display-mode: standalone)') Object.defineProperty(result, 'matches', {value: true});
                return result;
            };
        """
    sharing = "Object.defineProperty(navigator, 'share', {value: undefined, configurable: true});"
    if share != "unsupported":
        sharing = """
            Object.defineProperty(navigator, 'canShare', {value: data => data.files?.length === 1, configurable: true});
            Object.defineProperty(navigator, 'share', {value: data => {
                const file = data.files[0];
                window.sharedPdfFile = file;
                window.shareCalls.push({name: file.name, type: file.type, size: file.size,
                    activated: navigator.userActivation?.isActive === true});
                if (window.shareOutcome === 'cancel') return Promise.reject(new DOMException('Canceled', 'AbortError'));
                if (window.shareOutcome === 'failure') return Promise.reject(new DOMException('Unavailable', 'NotAllowedError'));
                return Promise.resolve();
            }, configurable: true});
        """
    return standalone + sharing + ("delete HTMLAnchorElement.prototype.download;" if not downloads else "") + f"""
        window.shareCalls = [];
        window.shareOutcome = '{share}';
        window.createdPdfUrls = [];
        window.revokedPdfUrls = [];
        const createPdfUrl = URL.createObjectURL.bind(URL);
        const revokePdfUrl = URL.revokeObjectURL.bind(URL);
        URL.createObjectURL = object => {{ const url = createPdfUrl(object); createdPdfUrls.push(url); return url; }};
        URL.revokeObjectURL = url => {{ revokedPdfUrls.push(url); return revokePdfUrl(url); }};
    """


@contextmanager
def pdf_page(browser, tmp_path, *, mode="navigator", share="success", downloads=True,
             surface="reader", javascript=True, controlled_fetch=False, width=390):
    app, path = make_table_fixture(tmp_path / "standalone.sqlite3")
    with running_room(app) as base, browser.new_context(
        viewport={"width": width, "height": 844 if width <= 760 else 1000},
        is_mobile=width <= 760, has_touch=width <= 760,
        java_script_enabled=javascript,
    ) as context:
        pdf_url = base + path + "/turns/1/pdf"
        expected = app.test_client().get(path + "/turns/1/pdf", base_url=base)
        assert expected.status_code == 200 and expected.mimetype == "application/pdf"
        context.add_init_script(setup_script(mode, share, downloads))
        if controlled_fetch:
            encoded = base64.b64encode(expected.data).decode("ascii")
            context.add_init_script("""
                window.pdfFetches = [];
                const realFetch = window.fetch.bind(window);
                window.fetch = (input, options) => {
                    const url = typeof input === 'string' ? input : input.url;
                    if (!url.endsWith('/turns/1/pdf')) return realFetch(input, options);
                    return new Promise((resolve, reject) => pdfFetches.push({url, options, resolve, reject}));
                };
                window.resolvePdfFetch = index => {
                    const bytes = Uint8Array.from(atob('""" + encoded + """'), char => char.charCodeAt(0));
                    pdfFetches[index].resolve(new Response(bytes, {status: 200,
                        headers: {'Content-Type': 'application/pdf'}}));
                };
            """)
        page = context.new_page()
        url = base + path + ("/turns/1/print" if surface == "print" else "")
        page.goto(url)
        assert page.evaluate("window.isSecureContext")
        yield page, context, pdf_url, expected.data


def assert_pdf_file(data):
    pdf = PdfReader(BytesIO(data))
    assert pdf_text(pdf).count(LAST_CELL_MARKER) == 1
    assert uris(pdf).count(LAST_CELL_URL) == 1
    assert uris(pdf).count(SOURCE_URL) == 1


def ready(page, sharing=True):
    dialog = page.locator("#answer-pdf-dialog")
    status = dialog.locator(".pdf-download-status")
    status.filter(has_text="Choose Share PDF" if sharing else "Use Save PDF").wait_for(state="visible")
    assert status.get_attribute("role") == "status"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    return dialog


@pytest.mark.parametrize("mode", ("navigator", "display"))
@pytest.mark.parametrize("surface", ("reader", "print"))
def test_standalone_prepares_real_pdf_then_shares_only_on_a_fresh_gesture(renderer, pdf_browser, tmp_path, mode, surface):
    with pdf_page(pdf_browser, tmp_path, mode=mode, surface=surface) as (page, context, pdf_url, _):
        opener = page.locator(".standalone-pdf-download")
        assert opener.is_visible() and page.locator(".browser-pdf-download").is_hidden()
        original_url = page.url
        with page.expect_response(lambda response: response.url == pdf_url) as received:
            opener.tap()
        response = received.value
        assert response.status == 200 and response.headers["content-type"].startswith("application/pdf")
        actual_pdf = response.body()
        assert_pdf_file(actual_pdf)
        dialog = ready(page)
        assert page.evaluate("window.shareCalls.length") == 0
        assert len(context.pages) == 1 and page.url == original_url
        assert dialog.get_by_role("button", name="Share PDF", exact=True).is_enabled()
        dialog.get_by_role("button", name="Share PDF", exact=True).tap()
        dialog.locator(".pdf-download-status").filter(has_text="Sharing finished").wait_for(state="visible")
        calls = page.evaluate("window.shareCalls")
        assert calls == [{"name": "scryraven-answer-1.pdf", "type": "application/pdf",
                          "size": len(actual_pdf), "activated": True}]
        digest = page.evaluate("""async () => {
            const hash = await crypto.subtle.digest('SHA-256', await sharedPdfFile.arrayBuffer());
            return [...new Uint8Array(hash)].map(value => value.toString(16).padStart(2, '0')).join('');
        }""")
        assert digest == hashlib.sha256(actual_pdf).hexdigest()
        dialog.get_by_role("button", name="Close", exact=True).tap()
        assert dialog.is_hidden() and opener.evaluate("el => el === document.activeElement")
        assert page.url == original_url


def test_save_only_fallback_downloads_the_prepared_blob_with_safe_new_context(renderer, pdf_browser, tmp_path):
    with pdf_page(pdf_browser, tmp_path, share="unsupported") as (page, _, pdf_url, _):
        original_url = page.url
        with page.expect_response(lambda response: response.url == pdf_url) as received:
            page.locator(".standalone-pdf-download").tap()
        actual_pdf = received.value.body()
        dialog = ready(page, sharing=False)
        assert dialog.get_by_role("button", name="Share PDF", exact=True).is_hidden()
        save = dialog.get_by_role("link", name="Save PDF", exact=True)
        assert save.get_attribute("href").startswith("blob:")
        assert save.get_attribute("target") == "_blank"
        assert "noopener" in save.get_attribute("rel").split()
        assert save.get_attribute("download") == "scryraven-answer-1.pdf"
        with page.expect_download() as prepared:
            save.tap()
        download = prepared.value
        destination = tmp_path / "prepared.pdf"
        download.save_as(destination)
        assert download.suggested_filename == "scryraven-answer-1.pdf"
        assert destination.read_bytes() == actual_pdf
        assert_pdf_file(destination.read_bytes())
        assert page.url == original_url and dialog.is_visible()
        safari = dialog.locator(".pdf-download-safari")
        assert safari.is_visible()
        safari.get_by_text("Open in Safari", exact=True).click()
        address = safari.locator("input")
        assert address.input_value() == pdf_url.rsplit("/turns/", 1)[0] + "#turn-1"
        assert address.evaluate("el => el.readOnly")


@pytest.mark.parametrize("outcome, message", (("cancel", "Sharing canceled"), ("failure", "Could not share the PDF")))
def test_canceled_or_failed_share_keeps_the_same_file_ready_for_another_try(
    renderer, pdf_browser, tmp_path, outcome, message,
):
    with pdf_page(pdf_browser, tmp_path, share=outcome) as (page, _, _, _):
        page.locator(".standalone-pdf-download").tap()
        dialog = ready(page)
        save = dialog.get_by_role("link", name="Save PDF", exact=True)
        blob_url = save.get_attribute("href")
        original_url = page.url
        dialog.get_by_role("button", name="Share PDF", exact=True).tap()
        dialog.locator(".pdf-download-status").filter(has_text=message).wait_for(state="visible")
        assert dialog.is_visible() and save.get_attribute("href") == blob_url
        assert dialog.get_by_role("button", name="Share PDF", exact=True).is_enabled()
        if outcome == "failure":
            assert dialog.get_by_text("Open in Safari", exact=True).is_visible()
        page.evaluate("window.shareOutcome = 'success'")
        dialog.get_by_role("button", name="Share PDF", exact=True).tap()
        dialog.locator(".pdf-download-status").filter(has_text="Sharing finished").wait_for(state="visible")
        assert page.evaluate("window.shareCalls.length") == 2
        assert page.url == original_url


def test_close_aborts_deduplicates_and_ignores_old_preparation_results(renderer, pdf_browser, tmp_path):
    with pdf_page(pdf_browser, tmp_path, controlled_fetch=True) as (page, _, _, _):
        opener = page.locator(".standalone-pdf-download")
        opener.tap()
        dialog = page.locator("#answer-pdf-dialog")
        assert dialog.is_visible()
        opener.evaluate("el => { el.click(); el.click(); }")
        assert page.evaluate("window.pdfFetches.length") == 1
        assert page.evaluate("window.pdfFetches[0].options.credentials") == "same-origin"
        assert page.evaluate("window.pdfFetches[0].options.mode") == "same-origin"
        dialog.get_by_role("button", name="Close", exact=True).tap()
        settle(page)
        assert page.evaluate("window.pdfFetches[0].options.signal.aborted")
        assert opener.evaluate("el => el === document.activeElement")
        opener.tap()
        assert page.evaluate("window.pdfFetches.length") == 2
        page.evaluate("window.resolvePdfFetch(1)")
        dialog = ready(page)
        current_url = dialog.get_by_role("link", name="Save PDF", exact=True).get_attribute("href")
        page.evaluate("window.resolvePdfFetch(0)")
        settle(page)
        assert dialog.get_by_role("link", name="Save PDF", exact=True).get_attribute("href") == current_url
        assert page.evaluate("window.createdPdfUrls.length") == 1
        dialog.get_by_role("button", name="Close", exact=True).tap()
        settle(page)
        assert page.evaluate("window.revokedPdfUrls.includes(window.createdPdfUrls[0])")
        assert opener.evaluate("el => el === document.activeElement")


@pytest.mark.parametrize("failure", ("status", "mime", "empty"))
def test_failed_preparation_stays_in_app_and_retry_is_explicit(renderer, pdf_browser, tmp_path, failure):
    with pdf_page(pdf_browser, tmp_path) as (page, context, pdf_url, actual_pdf):
        count = []

        def serve_pdf(route):
            count.append(route.request.url)
            if len(count) > 1:
                route.fulfill(status=200, content_type="application/pdf", body=actual_pdf)
            elif failure == "status":
                route.fulfill(status=503, content_type="text/plain", body="Synthetic unavailable renderer")
            elif failure == "mime":
                route.fulfill(status=200, content_type="text/html", body="Synthetic login response")
            else:
                route.fulfill(status=200, content_type="application/pdf", body=b"")

        context.route(pdf_url, serve_pdf)
        original_url = page.url
        page.locator(".standalone-pdf-download").tap()
        dialog = page.locator("#answer-pdf-dialog")
        dialog.locator(".pdf-download-status").filter(has_text="Could not prepare the PDF").wait_for(state="visible")
        assert len(count) == 1 and page.url == original_url and len(context.pages) == 1
        assert dialog.get_by_role("button", name="Share PDF", exact=True).is_hidden()
        assert dialog.get_by_role("link", name="Save PDF", exact=True).is_hidden()
        dialog.get_by_role("button", name="Retry", exact=True).tap()
        ready(page)
        assert len(count) == 2 and page.evaluate("window.shareCalls.length") == 0
        assert page.url == original_url


def test_unsupported_share_and_download_offer_a_copyable_safari_address(renderer, pdf_browser, tmp_path):
    with pdf_page(pdf_browser, tmp_path, share="unsupported", downloads=False) as (page, context, pdf_url, _):
        original_url = page.url
        page.locator(".standalone-pdf-download").tap()
        dialog = page.locator("#answer-pdf-dialog")
        dialog.locator(".pdf-download-status").filter(has_text="Open this answer in Safari").wait_for(state="visible")
        assert dialog.get_by_role("button", name="Share PDF", exact=True).is_hidden()
        assert dialog.get_by_role("link", name="Save PDF", exact=True).is_hidden()
        safari = dialog.locator(".pdf-download-safari")
        safari.get_by_text("Open in Safari", exact=True).click()
        address = safari.locator("input")
        assert address.is_visible() and address.input_value() == pdf_url.rsplit("/turns/", 1)[0] + "#turn-1"
        assert address.evaluate("el => el.readOnly")
        assert page.url == original_url and len(context.pages) == 1


@pytest.mark.parametrize("surface", ("reader", "print"))
@pytest.mark.parametrize("width", (390, 1440))
def test_regular_browser_download_and_no_script_print_fallback(renderer, pdf_browser, tmp_path, surface, width):
    with pdf_page(pdf_browser, tmp_path, mode="browser", surface=surface, width=width) as (page, _, _, _):
        link = page.locator(".browser-pdf-download")
        assert link.is_visible() and page.locator(".standalone-pdf-download").is_hidden()
        original_url = page.url
        with page.expect_download() as received:
            link.click()
        destination = tmp_path / "browser.pdf"
        received.value.save_as(destination)
        assert_pdf_file(destination.read_bytes())
        assert page.url == original_url and page.locator("#answer-pdf-dialog").is_hidden()
    with pdf_page(pdf_browser, tmp_path, mode="browser", surface=surface, javascript=False, width=width) as (page, _, _, _):
        assert page.locator(".browser-pdf-download").is_hidden()
        assert page.locator(".standalone-pdf-download").is_hidden()
        if surface == "reader":
            assert page.get_by_role("link", name=re.compile("^Print$")).is_visible()
        else:
            assert page.locator(".print-toolbar").is_visible()
            assert "Safari" in page.locator(".print-toolbar").inner_text()
