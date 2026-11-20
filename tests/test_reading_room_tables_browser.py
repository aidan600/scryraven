"""Read/Table user flows against full synthetic answers, without live I/O."""

import re
from contextlib import contextmanager
from io import BytesIO

import pytest
import test_citation_preview_browser as citation_browser
from markdown_it import MarkdownIt
from PIL import Image
from pypdf import PdfReader
from table_read_samples import (
    COMPACT_NUMERIC_TABLE,
    COMPLEX_TABLE_HTML,
    HEADERS,
    LAST_CELL_MARKER,
    LAST_CELL_URL,
    ROWS,
    SAVED_PASSAGE,
    SOURCE_URL,
    make_table_fixture,
)
from test_citation_preview_browser import running_room
from test_reading_room_print_browser import pdf_links

table_browser = citation_browser.citation_browser
browser = citation_browser.browser


def plain_cell(text):
    return text.replace("**", "").replace("*", "").replace("`", "").replace("[E1]", "[1]")


def normalized(text):
    return " ".join(text.split())


def settle(page):
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


@contextmanager
def table_page(browser, tmp_path, width=390, *, javascript=True, replacement=None, image=False):
    app, path = make_table_fixture(tmp_path / "tables.sqlite3")
    if image:
        output = BytesIO()
        Image.new("RGB", (3, 1), "#476b80").save(output, format="PNG")

        @app.get("/synthetic-table-image")
        def synthetic_image():
            return app.response_class(output.getvalue(), mimetype="image/png")

    with running_room(app) as base, browser.new_context(
        viewport={"width": width, "height": 844 if width <= 760 else 1000},
        is_mobile=width <= 760, has_touch=width <= 760, java_script_enabled=javascript,
    ) as context:
        context.route("https://example.org/**", lambda route: route.fulfill(body="Synthetic original source"))
        if replacement is not None or image:
            def answer_markup(route):
                response = route.fetch()
                body = response.text()
                if replacement is not None:
                    body = re.sub(r'(<article class="answer"[^>]*>).*?(</article>)',
                                  lambda match: match[1] + replacement + match[2], body, count=1, flags=re.S)
                if image:
                    body = body.replace("<td>The fictional Brie", '<td><img id="table-test-image" '
                                        'src="/synthetic-table-image" width="720" height="240" '
                                        'alt="Synthetic blue tasting strip">The fictional Brie', 1)
                route.fulfill(response=response, body=body)

            context.route(base + path, answer_markup)
        page = context.new_page()
        page.goto(base + path)
        yield page


def assert_no_page_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def assert_full_cells(page):
    cells = page.locator(".answer tbody tr")
    assert cells.count() == len(ROWS)
    for row_number, expected in enumerate(ROWS):
        actual = cells.nth(row_number).locator("td, th")
        assert actual.count() == len(expected)
        for cell_number, content in enumerate(expected):
            assert normalized(plain_cell(content)) in normalized(actual.nth(cell_number).inner_text())


@pytest.mark.parametrize("width", (320, 390, 430))
def test_read_full_paragraph_then_compare_same_attribute_and_switch_back(table_browser, tmp_path, width):
    with table_page(table_browser, tmp_path, width) as page:
        table = page.locator(".answer table")
        controls = page.locator(".table-controls")
        read = controls.get_by_role("button", name="Read", exact=True)
        grid = controls.get_by_role("button", name="Table", exact=True)
        assert "table-is-read" in table.get_attribute("class")
        assert read.get_attribute("aria-pressed") == "true"
        assert grid.get_attribute("aria-pressed") == "false"
        assert_full_cells(page)
        assert_no_page_overflow(page)

        first_attribute = table.locator("tbody tr").first.locator("td, th").nth(1)
        last_attribute = table.locator("tbody tr").last.locator("td, th").last
        assert first_attribute.bounding_box()["width"] >= page.locator(".table-scroll").bounding_box()["width"] - 45
        assert float(first_attribute.evaluate("el => getComputedStyle(el).fontSize").removesuffix("px")) >= 15
        assert first_attribute.evaluate("""el => {
            const style = getComputedStyle(el);
            return style.overflowY === 'visible' && style.textOverflow !== 'ellipsis' && style.maxHeight === 'none';
        }""")
        last_attribute.get_by_role("link", name=LAST_CELL_MARKER, exact=True).scroll_into_view_if_needed()
        settle(page)
        assert LAST_CELL_MARKER in last_attribute.inner_text()

        page.evaluate("""() => {
            window.originalTable = document.querySelector('.answer table');
            window.originalCells = [...window.originalTable.querySelectorAll('tbody td, tbody th')];
            window.originalCellText = window.originalCells.map(cell => cell.textContent);
            window.originalRichNodes = [...window.originalTable.querySelectorAll('strong, em, code, a, img')];
            window.originalCitation = window.originalTable.querySelector('a.citation');
        }""")
        grid.click()
        settle(page)
        assert "table-is-read" not in table.get_attribute("class")
        assert grid.get_attribute("aria-pressed") == "true"
        scroll = page.locator(".table-scroll")
        assert scroll.get_attribute("tabindex") == "0"
        assert scroll.get_attribute("role") == "region"
        assert scroll.get_attribute("aria-label")
        assert scroll.evaluate("el => el.scrollWidth > el.clientWidth")
        cue = page.locator(".table-scroll-cue")
        assert cue.is_visible() and cue.inner_text().strip()
        assert cue.get_attribute("aria-live") in (None, "off")

        # Compare one complete attribute across two rows within the same grid.
        first = table.locator("tbody tr").nth(0).locator("td, th").nth(1)
        second = table.locator("tbody tr").nth(1).locator("td, th").nth(1)
        first.scroll_into_view_if_needed()
        assert normalized(plain_cell(ROWS[0][1])) in normalized(first.inner_text())
        second.scroll_into_view_if_needed()
        assert normalized(plain_cell(ROWS[1][1])) in normalized(second.inner_text())
        row_heading = second.locator("xpath=parent::tr").locator("td, th").first
        remaining = scroll.evaluate("el => el.clientWidth") - row_heading.bounding_box()["width"]
        assert first.bounding_box()["width"] >= 160
        assert first.bounding_box()["width"] <= remaining + 2
        assert first.bounding_box()["width"] == pytest.approx(second.bounding_box()["width"], abs=1)
        assert row_heading.bounding_box()["x"] == pytest.approx(scroll.bounding_box()["x"], abs=1)
        assert row_heading.inner_text() == "Cheddar"
        scroll.evaluate("el => { el.scrollLeft = el.scrollWidth; }")
        settle(page)
        assert "←" in cue.inner_text() and "→" not in cue.inner_text()
        assert_no_page_overflow(page)

        read.click()
        settle(page)
        assert "table-is-read" in table.get_attribute("class")
        assert_full_cells(page)
        assert page.evaluate("""() => {
            const table = document.querySelector('.answer table');
            const cells = [...table.querySelectorAll('tbody td, tbody th')];
            return table === originalTable && cells.every((cell, index) => cell === originalCells[index]) &&
                cells.every((cell, index) => cell.textContent === originalCellText[index]) &&
                [...table.querySelectorAll('strong, em, code, a, img')].every((node, index) => node === originalRichNodes[index]) &&
                table.querySelector('a.citation') === originalCitation;
        }""")
        assert table.locator("strong").inner_text() == "soft, creamy centre"
        assert table.locator("em").inner_text() == "rounded, savoury flavour"
        assert table.locator("code").inner_text() == "cut-side"
        assert table.get_by_role("link", name=LAST_CELL_MARKER).get_attribute("href") == LAST_CELL_URL


@pytest.mark.parametrize("view", ("Read", "Table"))
def test_saved_passage_citation_returns_to_the_same_row_in_each_view(table_browser, tmp_path, view):
    with table_page(table_browser, tmp_path) as page:
        if view == "Table":
            page.locator(".table-controls").get_by_role("button", name="Table", exact=True).click()
        citation = page.locator('.answer a.citation[data-saved-passage]')
        citation.scroll_into_view_if_needed()
        settle(page)
        page.evaluate("window.savedTableCitation = document.querySelector('.answer a.citation')")
        before = page.locator(".reading-scroll").evaluate("el => el.scrollTop")
        sideways = page.locator(".table-scroll").evaluate("el => el.scrollLeft")
        citation.tap()
        selected = page.locator(".citation-support[open]")
        assert selected.locator("mark.support-text").inner_text() == SAVED_PASSAGE
        assert selected.locator("mark.support-text").is_visible()
        assert selected.locator("summary").first.evaluate("el => el === document.activeElement")
        excerpt = selected.locator('xpath=ancestor::details[contains(@class,"saved-excerpt")]')
        excerpt.get_by_role("link", name="Back to answer", exact=True).tap()
        settle(page)
        assert citation.evaluate("el => el === savedTableCitation && el === document.activeElement")
        assert page.locator(".reading-scroll").evaluate("el => el.scrollTop") == pytest.approx(before, abs=1)
        assert page.locator(".table-scroll").evaluate("el => el.scrollLeft") == pytest.approx(sideways, abs=1)
        assert "Brie" in citation.locator("xpath=ancestor::tr").inner_text()
        assert page.locator("#citation-preview").is_hidden()
        assert_no_page_overflow(page)


def test_table_accessibility_keyboard_and_images_keep_one_content_copy(table_browser, tmp_path):
    with table_page(table_browser, tmp_path, image=True) as page:
        table = page.locator(".answer table")
        image = table.get_by_role("img", name="Synthetic blue tasting strip")
        assert image.is_visible() and image.evaluate("el => el.complete && el.naturalWidth > 0")
        page.evaluate("window.originalTableImage = document.getElementById('table-test-image')")
        assert table.get_by_role("columnheader").count() == 3
        assert table.get_by_role("rowheader").count() == 3
        assert table.get_by_role("heading", name="Brie", exact=True).count() == 1
        assert table.locator("thead th").evaluate_all("cells => cells.every(cell => cell.scope === 'col')")
        assert page.locator(".table-read-label").evaluate_all(
            "labels => labels.length > 0 && labels.every(label => label.getAttribute('aria-hidden') === 'true')")
        assert page.evaluate("""() => {
            const ids = [...document.querySelectorAll('[id]')].map(el => el.id);
            return ids.length === new Set(ids).size;
        }""")
        assert table.locator("tbody tr").count() == 3
        assert table.get_by_role("link", name=LAST_CELL_MARKER).count() == 1
        grid = page.locator(".table-controls").get_by_role("button", name="Table", exact=True)
        grid.focus()
        grid.press("Enter")
        settle(page)
        assert grid.evaluate("el => el === document.activeElement")
        assert grid.get_attribute("aria-pressed") == "true"
        assert table.get_by_role("heading", name="Brie", exact=True).count() == 0
        assert table.get_by_role("columnheader").count() == 3
        assert table.get_by_role("rowheader").count() == 3
        page.locator(".table-scroll").focus()
        assert page.locator(".table-scroll").evaluate("el => el === document.activeElement")
        page.locator(".table-scroll").evaluate("el => { el.scrollLeft = 0; }")
        page.locator(".table-scroll").press("ArrowRight")
        assert page.locator(".table-scroll").evaluate("""el => new Promise(resolve => {
            function frame(left) {
                if (el.scrollLeft > 0 || left === 0) resolve(el.scrollLeft > 0);
                else requestAnimationFrame(() => frame(left - 1));
            }
            frame(30);
        })""")
        assert image.evaluate("el => el === originalTableImage")
        page.locator(".table-controls").get_by_role("button", name="Read", exact=True).click()
        assert image.evaluate("el => el === originalTableImage")
        assert_no_page_overflow(page)


def test_table_keyboard_preview_tracks_its_citation_during_sideways_scroll(table_browser, tmp_path):
    with table_page(table_browser, tmp_path) as page:
        page.locator(".table-controls").get_by_role("button", name="Table", exact=True).click()
        citation = page.locator('.answer a.citation[data-saved-passage]')
        citation.scroll_into_view_if_needed()
        settle(page)
        scroll = page.locator(".table-scroll")
        before_sideways = scroll.evaluate("el => el.scrollLeft")
        citation.focus()
        preview = page.locator("#citation-preview")
        assert preview.is_visible() and citation.get_attribute("aria-expanded") == "true"
        scroll.evaluate("el => { el.scrollLeft = el.scrollWidth; }")
        settle(page)
        assert preview.is_hidden() and citation.get_attribute("aria-expanded") == "false"
        scroll.evaluate("(el, position) => { el.scrollLeft = position; }", before_sideways)
        settle(page)
        citation.press("Space")
        assert preview.is_visible()
        saved = preview.get_by_role("link", name="View saved passage", exact=True)
        assert saved.is_visible()
        before = page.locator(".reading-scroll").evaluate("el => el.scrollTop")
        saved.click()
        selected = page.locator(".citation-support[open]")
        assert selected.locator("mark.support-text").inner_text() == SAVED_PASSAGE
        selected.locator('xpath=ancestor::details[contains(@class,"saved-excerpt")]').get_by_role(
            "link", name="Back to answer", exact=True,
        ).click()
        settle(page)
        assert citation.evaluate("el => el === document.activeElement")
        assert page.locator(".reading-scroll").evaluate("el => el.scrollTop") == pytest.approx(before, abs=1)
        assert scroll.evaluate("el => el.scrollLeft") == pytest.approx(before_sideways, abs=1)
        assert_no_page_overflow(page)


def test_compact_and_complex_tables_remain_scrollable_grids(table_browser, tmp_path):
    numeric = MarkdownIt("commonmark").enable("table").render(COMPACT_NUMERIC_TABLE)
    complex_markup = COMPLEX_TABLE_HTML.replace('<th colspan="2">', '<th colspan="2" scope="colgroup">')
    with table_page(table_browser, tmp_path, width=320, replacement=numeric + complex_markup) as page:
        assert page.locator(".answer table").count() == 2
        assert page.locator(".table-controls").count() == 0
        assert page.locator(".table-is-read").count() == 0
        assert page.locator(".answer table").first.get_by_role("columnheader").count() == 3
        assert "7" in page.locator(".answer table").first.inner_text()
        complex_table = page.locator(".answer table").last
        assert complex_table.locator('[colspan="2"]').count() == 1
        assert complex_table.locator('[colspan="2"]').get_attribute("scope") == "colgroup"
        assert complex_table.locator('[rowspan="2"]').count() == 1
        assert page.locator(".table-scroll").count() == 2
        assert page.locator(".table-scroll").evaluate_all(
            "regions => regions.every(region => getComputedStyle(region).overflowX === 'auto')")
        assert_no_page_overflow(page)


def test_a_single_paragraph_cell_gets_the_read_layout(table_browser, tmp_path):
    markdown = '| Cheese | Description |\n| --- | --- |\n| Brie | ' + ROWS[0][1] + ' |'
    markup = MarkdownIt('commonmark').enable('table').render(markdown)
    with table_page(table_browser, tmp_path, width=320, replacement=markup) as page:
        assert page.locator('.table-controls').get_by_role('button', name='Read', exact=True).get_attribute('aria-pressed') == 'true'
        assert 'table-is-read' in page.locator('.answer table').get_attribute('class')
        assert normalized(ROWS[0][1].replace('**', '')) in normalized(page.locator('tbody td').last.inner_text())
        assert_no_page_overflow(page)


def test_desktop_and_no_script_keep_the_complete_semantic_grid(table_browser, tmp_path):
    with table_page(table_browser, tmp_path, width=1440) as page:
        assert "table-is-read" not in (page.locator(".answer table").get_attribute("class") or "")
        assert page.locator(".table-controls").is_hidden()
        assert page.locator(".answer table").get_by_role("columnheader").count() == 3
        assert_full_cells(page)
        assert_no_page_overflow(page)
    with table_page(table_browser, tmp_path, width=320, javascript=False) as page:
        assert page.locator(".answer table").count() == 1
        assert page.locator(".table-controls").count() == 0
        assert page.locator(".table-is-read").count() == 0
        assert_full_cells(page)
        assert page.locator(".answer table").evaluate("el => getComputedStyle(el).overflowX") == "auto"
        assert_no_page_overflow(page)


@pytest.mark.parametrize("view", ("Read", "Table"))
def test_reader_and_protected_pdf_export_include_the_complete_last_cell_once(browser, tmp_path, view):
    with table_page(browser, tmp_path) as page:
        if view == "Table":
            page.locator(".table-controls").get_by_role("button", name="Table", exact=True).click()
        for standalone in (False, True):
            if standalone:
                page.get_by_role("link", name="Print / Save as PDF", exact=True).click()
                assert page.url.endswith("/turns/1/print")
                page.get_by_role("button", name="Print / Save as PDF", exact=True).wait_for(state="visible")
            page.emulate_media(media="print")
            pdf = PdfReader(BytesIO(page.pdf(prefer_css_page_size=True)))
            page.emulate_media(media="screen")
            # PDF extraction inserts whitespace at a wrapped existing hyphen.
            extracted = " ".join(pdf_page.extract_text() for pdf_page in pdf.pages)
            text = normalized(re.sub(r"(?<=\w)-\s+(?=\w)", "-", extracted))
            assert text.count(LAST_CELL_MARKER) == 1
            assert all(header in text for header in HEADERS)
            assert all(normalized(plain_cell(cell)) in text for row in ROWS for cell in row)
            assert "More columns" not in text and "Back to answer" not in text
            links = pdf_links(pdf)
            assert sum(link.get("/A", {}).get("/URI") == LAST_CELL_URL for link in links) == 1
            assert sum(link.get("/A", {}).get("/URI") == SOURCE_URL for link in links) == 1
            assert any((link.get("/Dest") or "").lstrip("/") == "print-turn-1-source-1" for link in links)
