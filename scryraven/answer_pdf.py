"""Render trusted answer markup with local fonts and no resource fetches."""

from functools import cache
from pathlib import Path


class PdfUnavailable(Exception):
    """The renderer is unavailable or requested a resource."""


@cache
def _renderer():
    try:
        from weasyprint import CSS, HTML
        from weasyprint.urls import FatalURLFetchingError, URLFetcher
    except (ImportError, OSError):
        return None

    class NoResources(URLFetcher):
        def fetch(self, url, headers=None):
            # Hyperlinks are emitted as PDF annotations, never fetched.
            raise FatalURLFetchingError("PDF resources are disabled")

    fetcher = NoResources()
    css = CSS(string=Path(__file__).with_name("static").joinpath("answer_pdf.css").read_text(encoding="utf-8"),
              url_fetcher=fetcher)
    return HTML, css, fetcher, FatalURLFetchingError


def available():
    return _renderer() is not None


def render_pdf(markup: str, *, base_url: str) -> bytes:
    renderer = _renderer()
    if renderer is None:
        raise PdfUnavailable()
    html, css, fetcher, blocked_resource = renderer
    try:
        return html(string=markup, base_url=base_url, url_fetcher=fetcher).write_pdf(stylesheets=[css])
    except blocked_resource:
        raise PdfUnavailable() from None
