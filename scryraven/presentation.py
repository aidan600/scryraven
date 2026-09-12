"""One answer's deterministic citations and local view; no research or storage."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from html import escape
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

from scryraven.sources import Evidence

if TYPE_CHECKING:
    from scryraven.research import Result
    from scryraven.session_store import SessionTurn


@dataclass(frozen=True)
class Citation:
    number: int
    source_id: str
    title: str
    url: str
    materials: tuple[Evidence, ...]


@dataclass(frozen=True)
class CitationUse:
    """A validated reference's character span in the final numeric answer."""

    number: int
    start: int
    end: int


def _source_label(citation: Citation) -> str:
    if title := " ".join(citation.title.split()):
        return title
    # Missing display metadata does not license generating a publication title
    # from source content. Label the URL's filename as a filename instead.
    try:
        parsed = urlsplit(citation.url)
    except ValueError:
        return "Untitled source"
    filename = unquote(parsed.path.rsplit("/", 1)[-1])
    if filename.lower().endswith(".pdf"):
        return "Publication file: " + " ".join(filename.replace("_", " ").split())
    return parsed.hostname or "Untitled source"


def render_cli(result: Result | SessionTurn) -> str:
    sources = "\n".join(
        f"[{item.number}] {_source_label(item)}\n    {item.url}"
        for item in result.citations
    )
    return result.answer + ("\n\nSources\n" + sources if sources else "")


def _answer_html(result: Result | SessionTurn) -> str:
    # Only spans emitted by validation become links. Ordinary numeric brackets
    # in prose are not citations. Insert trusted fragment destinations before
    # Markdown parsing; raw HTML, images and autolinks remain disabled.
    parts = []
    previous = 0
    for use in result.citation_uses:
        parts.extend((result.answer[previous:use.start], f"[[{use.number}]](#source-{use.number})"))
        previous = use.end
    parts.append(result.answer[previous:])
    markdown = MarkdownIt("commonmark", {"html": False}).enable("table").disable(["image", "autolink"])
    return markdown.render("".join(parts))


def _source_link(url: str) -> str:
    # Defense at the HTML boundary, also for callers constructing results offline.
    # No URL is synthesized from an evidence offset or document locator.
    try:
        parsed = urlsplit(url)
        allowed = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                   and not parsed.username and not parsed.password
                   and not any(char.isspace() or ord(char) < 32 for char in url))
    except ValueError:
        allowed = False
    if not allowed:
        return '<p class="source-url">Original source URL unavailable.</p>'
    return (f'<p class="source-url"><a href="{escape(url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">Open original publication <span aria-hidden="true">↗</span></a>'
            f'<br><span>{escape(url)}</span></p>')


_ACQUISITION_LABELS = {
    "provider_highlights": "Extractive highlights. Selections may be noncontiguous or omit surrounding context.",
    "fetched_source": "Extracted source text.",
    "targeted_view": "Selected slice of extracted text. Slice boundaries are not original-document page locations.",
}


def _source_html(citation: Citation) -> str:
    materials = "".join(
        '<section class="material">'
        f'<h3>Selection {index}</h3><p class="acquisition">{_ACQUISITION_LABELS[item.acquisition]}</p>'
        f'<pre><code>{escape(item.content)}</code></pre></section>'
        for index, item in enumerate(citation.materials, 1)
    )
    return (
        f'<details id="source-{citation.number}">'
        f'<summary><span class="source-number">[{citation.number}]</span> '
        f'{escape(_source_label(citation))}</summary>'
        '<div class="source-body">' + _source_link(citation.url)
        + '<h2>Material ScryRaven used from this source</h2>'
        '<p class="scope">The citation refers to this source and its selected material, '
        'not one exact proof passage. These selections may not include the whole publication.</p>'
        + materials + '</div></details>'
    )


_STYLE = """
:root { color-scheme: light; font: 17px/1.65 system-ui, sans-serif; color: #202e35; background: #f8f9f7; }
* { box-sizing: border-box; }
body { margin: 0; }
main { max-width: 850px; margin: 0 auto; padding: 46px 28px 80px; }
.brand { color: #526660; font-size: .78rem; font-weight: 700; letter-spacing: .13em; text-transform: uppercase; }
header { border-bottom: 1px solid #d7dfda; padding-bottom: 24px; margin-bottom: 28px; }
h1 { font-size: clamp(1.5rem, 3.5vw, 2rem); line-height: 1.3; font-weight: 650; margin: 12px 0 0; }
h2 { font-size: 1.12rem; line-height: 1.4; margin: 1.65em 0 .55em; }
h3, h4, h5, h6 { font-size: 1rem; margin: 1.3em 0 .45em; }
p { margin: 0 0 1em; }
.answer { overflow-wrap: anywhere; }
.answer > :first-child { margin-top: 0; }
.answer h1 { font-size: 1.2rem; margin-top: 1.5em; }
a { color: #226653; text-underline-offset: 3px; }
.answer a { font-size: .8em; font-weight: 650; white-space: nowrap; text-decoration: none; padding: 0 .08em; }
a:hover { text-decoration: underline; }
:focus-visible { outline: 2px solid #226653; outline-offset: 4px; }
ul, ol { padding-left: 1.4em; margin: .5em 0 1.1em; }
li { margin: .35em 0; }
table { display: block; width: 100%; overflow-x: auto; border-collapse: collapse; margin: 1.2em 0; font-size: .92rem; }
th, td { text-align: left; vertical-align: top; padding: .6em .85em; border: 1px solid #d7dfda; }
th { background: #eef2ee; }
blockquote { margin: 1em 0; padding-left: 1em; border-left: 3px solid #b2c4b9; }
.sources { margin-top: 38px; border-top: 1px solid #d7dfda; padding-top: 8px; }
.sources > h2 { font-size: .85rem; color: #526660; margin: 18px 0 12px; }
details { border: 1px solid #d7dfda; border-radius: 8px; margin: 10px 0; background: #fff; scroll-margin-top: 20px; }
summary { padding: 14px 18px; cursor: pointer; font-size: .92rem; font-weight: 550; overflow-wrap: anywhere; }
.source-number { color: #226653; margin-right: 6px; }
.source-body { padding: 4px 20px 20px; }
.source-body h2 { font-size: 1rem; margin-top: 20px; }
.source-url, .scope, .acquisition { font-size: .82rem; color: #58666a; }
.source-url span { overflow-wrap: anywhere; }
.material { margin-top: 22px; }
.material h3 { font-size: .85rem; margin-bottom: 3px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; font: .86rem/1.65 system-ui, sans-serif;
      background: #f5f7f4; border-left: 2px solid #c9d7ce; padding: 16px; margin: 10px 0 0; }
pre code { font: inherit; }
@media (max-width: 560px) { main { padding: 26px 18px 50px; } .source-body { padding: 4px 14px 16px; } }
@media print { body { background: #fff; } main { max-width: none; padding: 0; } }
"""

# Fixed code only: no model, question or evidence string is interpolated here.
_SCRIPT = """
function revealSource() {
  if (!/^#source-[0-9]+$/.test(location.hash)) return;
  const source = document.getElementById(location.hash.slice(1));
  if (!source || source.tagName !== 'DETAILS') return;
  source.open = true;
  source.querySelector('summary').focus({preventScroll: true});
  source.scrollIntoView({block: 'start'});
}
document.querySelector('.answer').addEventListener('click', event => {
  const link = event.target.closest('a');
  if (link && link.getAttribute('href') === location.hash) revealSource();
});
window.addEventListener('hashchange', revealSource);
revealSource();
"""


def _hash_allowance(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


def render_html(question: str, result: Result | SessionTurn) -> str:
    """Render a self-contained artifact with escaped source text and fixed assets."""
    policy = ("default-src 'none'; base-uri 'none'; form-action 'none'; "
              f"style-src {_hash_allowance(_STYLE)}; script-src {_hash_allowance(_SCRIPT)}")
    sources = ('<section class="sources" aria-label="Sources"><h2>Sources · open to inspect</h2>'
               + "".join(_source_html(item) for item in result.citations) + '</section>') if result.citations else ""
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        f'<meta http-equiv="Content-Security-Policy" content="{escape(policy, quote=True)}">'
        f'<title>ScryRaven answer</title><style>{_STYLE}</style></head><body><main>'
        '<header><div class="brand">ScryRaven</div>'
        f'<h1>{escape(question)}</h1></header><article class="answer" aria-label="Answer">'
        + _answer_html(result) + '</article>' + sources
        + f'</main><script>{_SCRIPT}</script></body></html>\n'
    )
