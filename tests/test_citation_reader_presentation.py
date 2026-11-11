"""Exact-source highlighting and mechanical use-specific PDF locators."""

from dataclasses import asdict
from hashlib import sha256
from html.parser import HTMLParser

import pytest

from scryraven.presentation import Citation, CitationUse, answer_html, render_html, source_body_html
from scryraven.session_store import SessionTurn
from scryraven.sources import Evidence, SupportRegion


class TextNodes(HTMLParser):
    def __init__(self, html, css_class):
        super().__init__(convert_charrefs=True)
        self.css_class, self.nodes, self.capture = css_class, [], None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if self.css_class in dict(attrs).get("class", "").split():
            self.capture = tag
            self.nodes.append("")

    def handle_endtag(self, tag):
        if tag == self.capture:
            self.capture = None

    def handle_data(self, data):
        if self.capture:
            self.nodes[-1] += data


def region(material, text):
    start = material.content.index(text)
    return SupportRegion(material.id, start, start + len(text),
                         sha256(material.content.encode()).hexdigest(), sha256(text.encode()).hexdigest())


def citation(materials, *, document=False):
    return Citation(1, "D1" if document else "E1", "Saved publication", "" if document else "https://example.org",
                    tuple(materials), "user_document" if document else "web",
                    "D1" if document else None, "bulletin.pdf" if document else None,
                    1 if document else None, 9 if document else None)


def document_material(text, page_start, page_end=None, start=9000):
    end = start + len(text)
    return Evidence(f"D1@{start}:{end}", "", "bulletin.pdf", text, "targeted_view",
                    source_id="D1", parent_id="D1", start_char=start, end_char=end,
                    source_kind="user_document", document_id="D1", filename="bulletin.pdf",
                    page_start=page_start, page_end=page_end or page_start,
                    visual_analysis=False, textless_page_count=0)


def test_highlighted_support_and_nearby_text_are_exact_retained_characters():
    body = 'Leading context.\nAlpha is seven & <script>unsafe()</script>.\nAn exception applies.\nTrailing context.'
    material = Evidence("E1", "https://example.org", "Saved publication", body)
    selected = ['Alpha is seven & <script>unsafe()</script>.', 'An exception applies.']
    use = CitationUse(1, 0, 3, tuple(region(material, text) for text in selected))
    before = asdict(use)
    html = source_body_html(citation([material]), uses=(use,))
    assert TextNodes(html, "support-text").nodes == selected
    # Nearby selections flow together in one exact source excerpt instead of duplicate cards.
    assert TextNodes(html, "source-prose").nodes == [body, body]
    assert '<script>unsafe()' not in html and '&lt;script&gt;' in html
    assert '<pre class="material-text support-text"' not in html
    assert html.index('Open original publication') < html.index('Saved passage for this citation')
    assert html.index('Saved passage for this citation') < html.index('Surrounding context') < html.index('Full saved material')
    assert asdict(use) == before


@pytest.mark.parametrize(("page_start", "page_end", "label"), [(4, 4, "Physical PDF page 4"),
                                                             (4, 6, "Physical PDF pages 4–6")])
def test_pdf_support_uses_saved_view_page_metadata_not_offsets(page_start, page_end, label):
    material = document_material("A weather exception applies.", page_start, page_end)
    use = CitationUse(1, 0, 3, (region(material, "weather exception"),))
    html = source_body_html(citation([material], document=True), uses=(use,),
                            original_href="/sessions/" + "a" * 32 + "/documents/D1/original")
    assert TextNodes(html, "support-location").nodes == [label, label]
    assert TextNodes(html, "support-text").nodes == ["weather exception"]
    assert 'Open original PDF' in html
    assert '9000' not in html  # Coordinates remain custody, not invented page locators.


def test_pdf_support_locators_follow_only_this_uses_materials():
    materials = tuple(document_material(text, page, start=page * 100)
                      for page, text in [(2, "Early fact."), (9, "Later exception.")])
    uses = (CitationUse(1, 0, 3, (region(materials[0], "Early fact."),)),
            CitationUse(1, 4, 7, (region(materials[1], "Later exception."),)))
    first = source_body_html(citation(materials, document=True), uses=uses[:1])
    second = source_body_html(citation(materials, document=True), uses=uses[1:])
    assert TextNodes(first, "support-location").nodes == ["Physical PDF page 2", "Physical PDF page 2"]
    assert TextNodes(second, "support-location").nodes == ["Physical PDF page 9", "Physical PDF page 9"]
    assert TextNodes(first, "support-text").nodes == ["Early fact."]
    assert TextNodes(second, "support-text").nodes == ["Later exception."]
    # The overall source can still cover both saved views in full material inspection.
    assert "pp. 2, 9" in first and "pp. 2, 9" in second


def test_generic_source_body_has_no_use_specific_highlights_or_locators():
    material = Evidence("E1", "https://example.org", "Saved publication", "A saved fact.")
    html = source_body_html(citation([material]))
    assert 'Saved passage for this citation' not in html
    assert not TextNodes(html, "support-text").nodes
    assert not TextNodes(html, "support-location").nodes
    assert material.content in html


def test_reader_does_not_infer_a_formal_pinpoint_from_a_saved_pdf_page():
    text = "Reporter page 421 — The weather exception applies."
    material = document_material(text, 4)
    saved = citation([material], document=True)
    answer = "The weather exception applies. *Example v. Town*, 88 Test Rep. 419, 421. [1]"
    offset = answer.index("[1]")
    use = CitationUse(1, offset, offset + 3, (region(material, "The weather exception applies."),))
    turn = SessionTurn("Does the weather exception apply?", answer, None, "supported", "supported",
                       (material,), (saved,), (use,))
    html = answer_html(turn, source_prefix="turn-1-source-", citation_previews=True)
    body = source_body_html(saved, uses=(use,), source_anchor="turn-1-source-1")
    anchor = f"turn-1-source-1-passage-{offset}"
    assert f'href="#{anchor}"' in html and f'id="{anchor}"' in body
    assert "88 Test Rep. 419, 421." in html
    assert TextNodes(body, "support-location").nodes == ["Physical PDF page 4", "Physical PDF page 4"]


def test_standalone_uses_the_same_exact_highlighting_and_occurrence_markers():
    material = Evidence("E1", "https://example.org", "Saved publication", "Alpha is seven. Omega is nine.")
    answer = "Alpha [1]. Omega [1]."
    uses = (CitationUse(1, 6, 9, (region(material, "Alpha is seven."),)),
            CitationUse(1, 17, 20, (region(material, "Omega is nine."),)))
    turn = SessionTurn("What are the values?", answer, None, "supported", "supported",
                       (material,), (citation([material]),), uses)
    html = render_html(turn.question, turn)
    assert TextNodes(html, "support-text").nodes == ["Alpha is seven.", "Omega is nine."]
    assert 'data-citation-start="6"' in html and 'data-citation-start="17"' in html
    assert 'mark class="support-text"' in html and 'source-prose' in html
