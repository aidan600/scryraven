"""Presentation promises through the ordinary path, without live providers."""

from dataclasses import replace
from html.parser import HTMLParser

import pytest
from test_walking_skeleton import Model, analysis, author, done, orient, read, relevance, search_for

from core.exa_transport import DiscoveryCandidate, FetchedMaterial
from scryraven import __main__ as cli
from scryraven import research
from scryraven.presentation import _SCRIPT, render_cli, render_html
from scryraven.sources import Evidence, exact_view

QUESTION = "What is the weight limit?"
URL = "https://example.test/rules"


def answer(draft="The limit is **16 pounds**. [E1]", *, title="Official rules", content="Maximum: 16 pounds."):
    model = Model(orient(), search_for(), read("C1"), relevance("E1"), analysis(), author(draft))
    return research.run(QUESTION, model=model,
                        search=lambda q: [DiscoveryCandidate(title, URL, "navigation")],
                        fetch=lambda url: FetchedMaterial(url, content))


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.pre = []
        self.in_pre = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "pre":
            self.in_pre = True
            self.pre.append("")

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data):
        self.text.append(data)
        if self.in_pre:
            self.pre[-1] += data


def test_first_validated_use_orders_sources_and_reuses_numbers_without_inline_titles():
    sources = [DiscoveryCandidate(f"Long publication title {i}", URL + str(i), "navigation") for i in range(1, 4)]
    model = Model(orient(), search_for(), read("C1", "C2", "C3"), relevance("E1", "E2", "E3"),
                  analysis(refs=("E1", "E2", "E3")),
                  author("First. [E2] Next. [[E1, E2]] Again. [[E1]] An ordinary [1] in prose."))
    result = research.run(QUESTION, model=model, search=lambda q: sources,
                          fetch=lambda url: FetchedMaterial(url, "Maximum: 16 pounds."))
    assert result.answer == "First. [1] Next. [2] [1] Again. [2] An ordinary [1] in prose."
    assert [(c.number, c.source_id, c.url) for c in result.citations] == [(1, "E2", URL + "2"), (2, "E1", URL + "1")]
    assert "publication" not in result.answer
    assert [result.answer[use.start:use.end] for use in result.citation_uses] == ["[1]", "[2]", "[1]", "[2]"]
    html = render_html(QUESTION, result)
    assert html == render_html(QUESTION, result)
    page = Page(html)
    assert [a["href"] for tag, a in page.tags if tag == "a" and a["href"].startswith("#")] == [
        "#source-1", "#source-2", "#source-1", "#source-2",
    ]
    assert [a["id"] for tag, a in page.tags if tag == "details"] == ["source-1", "source-2"]
    assert "Long publication title 3" not in html
    assert render_cli(result).count("Long publication title 2") == 1


def test_selected_source_slices_are_exact_grouped_material_without_manufactured_locators():
    result = answer()
    parent = Evidence("E1", URL + ".pdf", "Original publication", "\nFirst <quoted> material.\nUNSELECTED\nLast & material.\n")
    selected = (exact_view(parent, 0, 26), exact_view(parent, 37, len(parent.content)))
    citation = replace(result.citations[0], url=parent.url, title=parent.title, materials=selected)
    result = replace(result, selected_evidence=selected, citations=(citation,))
    page = Page(render_html(QUESTION, result))
    assert page.pre == [item.content for item in selected]
    assert "UNSELECTED" not in "".join(page.text)
    assert [attrs["href"] for tag, attrs in page.tags if tag == "a"] == ["#source-1", parent.url]
    assert not any("open" in attrs for tag, attrs in page.tags if tag == "details")
    assert "not one exact proof passage" in "".join(page.text)
    assert "not original-document page locations" in "".join(page.text)


def test_markdown_structure_and_citations_render_without_adding_an_answer_template():
    simple = Page(render_html(QUESTION, answer()))
    assert not any(tag == "table" for tag, attrs in simple.tags)
    structured = answer("The limit depends on class. [E1]\n\n## Classes\n\n"
                        "| Class | Limit |\n| --- | --- |\n| Standard | 16 pounds. [E1] |\n\n"
                        "- Apply the condition. [E1]\n\nA separate qualification. [E1]")
    page = Page(render_html(QUESTION, structured))
    assert {"h2", "table", "th", "td", "ul", "li"} <= {tag for tag, attrs in page.tags}
    assert len([attrs for tag, attrs in page.tags if tag == "a" and attrs["href"] == "#source-1"]) == 4


@pytest.mark.parametrize("draft", ["A quoted number: `[1]`.", "```text\nNumber: [1]\n```",
                                   "    Number: [1]"])
def test_ordinary_numbers_inside_code_do_not_become_citations(draft):
    page = Page(render_html(QUESTION, answer(draft + "\n\nThe source. [E1]")))
    assert [a["href"] for tag, a in page.tags if a.get("class") == "citation"] == ["#source-1"]
    assert "Number: [1]" in "".join(page.text) or "A quoted number: [1]" in "".join(page.text)


def test_markdown_table_alignment_uses_csp_compatible_classes():
    page = Page(render_html(QUESTION, answer("A table. [E1]\n\n| Left | Center | Right |\n"
                                          "| :--- | :---: | ---: |\n| A | B | C |")))
    cells = [attrs for tag, attrs in page.tags if tag in {"th", "td"}]
    assert [attrs["class"] for attrs in cells] == ["align-left", "align-center", "align-right"] * 2
    assert not any("style" in attrs for attrs in cells)


def test_unable_empty_evidence_has_no_invented_sources_or_citations():
    model = Model(orient(), done(), analysis("unable", refs=()),
                  author("The available evidence did not establish the weight limit."))
    result = research.run(QUESTION, model=model, search=lambda q: [], fetch=lambda url: None)
    assert result.posture == "unable"
    assert result.citations == result.citation_uses == result.selected_evidence == ()
    assert render_cli(result) == result.answer
    assert not any(tag in {"details", "a"} for tag, attrs in Page(render_html(QUESTION, result)).tags)


@pytest.mark.parametrize("draft", ["16 pounds.", "16 pounds. [1]", "16 pounds. [E2]", "16 pounds. [E1@0:10]",
                                    "16 pounds. [E1] [E", "16 pounds. [E1] [[E1]]]", "16 pounds. [E999]"])
def test_presentation_cannot_bypass_required_or_validated_aliases(draft):
    with pytest.raises(research.RunError) as caught:
        answer(draft)
    assert caught.value.stage == "citations"


@pytest.mark.parametrize("payload", [
    '<script>window.PWNED = true</script>',
    '<img src=x onerror="window.PWNED=true">',
    '<svg onload="window.PWNED=true"></svg>',
    '</style><iframe srcdoc="&lt;script&gt;alert(1)&lt;/script&gt;"></iframe>',
    '&#60;script&#62;window.PWNED=true&#60;/script&#62;',
])
def test_question_model_and_source_strings_are_inert_text(payload):
    content = "\nExact selection:\n" + payload + "\n& < > \" '"
    result = answer(payload + " The limit is 16 pounds. [E1]", title=payload, content=content)
    html = render_html(payload, result)
    page = Page(html)
    assert page.pre == [content]
    assert len([tag for tag, attrs in page.tags if tag == "script"]) == 1
    assert f"<script>{_SCRIPT}</script>" in html
    assert not any(tag in {"img", "iframe", "svg", "object", "embed", "base"} for tag, attrs in page.tags)
    assert not any(name.lower().startswith("on") for tag, attrs in page.tags for name in attrs)
    csp = next(a["content"] for tag, a in page.tags if tag == "meta" and a.get("http-equiv") == "Content-Security-Policy")
    assert "default-src 'none'" in csp and "script-src 'sha256-" in csp
    assert "unsafe-inline" not in csp


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
                                "//example.test/source", "https://user@example.test/", "https://example.test/\n"])
def test_unsafe_source_url_cannot_become_an_active_link(url):
    result = answer()
    result = replace(result, citations=(replace(result.citations[0], url=url),))
    assert [a["href"] for tag, a in Page(render_html(QUESTION, result)).tags if tag == "a"] == ["#source-1"]


def test_source_url_attribute_is_escaped_and_original_url_remains_accessible():
    result = answer()
    url = 'https://example.test/?q="<script>alert(1)</script>&kind=source'
    result = replace(result, citations=(replace(result.citations[0], url=url),))
    page = Page(render_html(QUESTION, result))
    assert [a["href"] for tag, a in page.tags if tag == "a"] == ["#source-1", url]
    assert len([tag for tag, attrs in page.tags if tag == "script"]) == 1


@pytest.mark.parametrize("url,expected", [
    ("https://example.test/2025/Acceptable_Use%20Policy.pdf", "Publication file: Acceptable Use Policy.pdf"),
    ("https://example.test/", "example.test"),
    ("https://example.test/%3Cscript%3Eevil%3C%2Fscript%3E.pdf", "Publication file: <script>evil</script>.pdf"),
])
def test_missing_title_uses_honest_escaped_url_metadata_without_repeating_the_url(url, expected):
    result = answer(title=" ")
    citation = replace(result.citations[0], url=url)
    result = replace(result, citations=(citation,))
    cli_text = render_cli(result)
    assert f"[1] {expected}\n" in cli_text
    assert cli_text.count(url) == 1
    page = Page(render_html(QUESTION, result))
    assert expected in "".join(page.text)
    assert [a["href"] for tag, a in page.tags if tag == "a"] == ["#source-1", url]
    assert len([tag for tag, attrs in page.tags if tag == "script"]) == 1
    assert citation.title == " " and citation.materials == result.selected_evidence


def test_cli_writes_local_view_and_keeps_diagnostics_out_of_ordinary_output(monkeypatch, capsys, tmp_path):
    result = answer()
    monkeypatch.setattr(cli, "run", lambda question: result)
    output = tmp_path / "answer.html"
    assert cli.main([QUESTION, "--html", str(output)]) == 0
    captured = capsys.readouterr()
    assert captured.out == render_cli(result) + "\n"
    assert captured.err == ""
    html = output.read_text(encoding="utf-8")
    assert html == render_html(QUESTION, result)
    assert "posture" not in html and "stop_reason" not in html and "E1" not in html
    assert "trace" not in captured.out
    assert cli.main([QUESTION, "--html", str(tmp_path / "absent" / "answer.html")]) == 1
    captured = capsys.readouterr()
    assert result.answer in captured.out and "could not write" in captured.err
