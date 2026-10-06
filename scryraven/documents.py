"""Session PDF custody: text extraction and page mapping. No OCR, vision, or model calls."""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import quote

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from scryraven.sources import TARGETED_SOURCE_CHARACTERS, Evidence

# Operating bounds, not a judgment that a smaller PDF is semantically complete.
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 500
MAX_EXTRACTED_CHARACTERS = 2_000_000
MAX_FILENAME_LENGTH = 180

TEXT_ONLY_WARNING = (
    "ScryRaven analyzes extracted PDF text only. Images and scanned content are not analyzed."
)
ALREADY_ATTACHED_NOTICE = "This PDF is already attached to this session."

DOCUMENT_ID = re.compile(r"D[1-9]\d*\Z")
DOCUMENT_VIEW_ID = re.compile(r"(D[1-9]\d*)@((?:0|[1-9]\d*)):((?:0|[1-9]\d*))\Z")
_ORIGINAL_HREF = re.compile(r"/sessions/[0-9a-f]{32}/documents/D[1-9]\d*/original\Z")

DOCUMENT_ERROR_MESSAGES = {
    "pdf_required": "Choose a PDF to attach.",
    "pdf_type_rejected": "Attach a PDF file.",
    "pdf_too_large": "That PDF exceeds the 20 MB attachment limit.",
    "pdf_too_many_pages": "That PDF exceeds the 500-page limit.",
    "pdf_too_much_text": "That PDF exceeds the extracted-text limit.",
    "pdf_malformed": "That file could not be read as a PDF.",
    "pdf_encrypted": "Password-protected PDFs cannot be attached.",
    "pdf_no_text": (
        "That PDF has no extractable text. " + TEXT_ONLY_WARNING
    ),
}


class DocumentRejected(Exception):
    """Fixed public code. The message is the code, never parser or path text."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PreparedDocument:
    """Validated upload before a session assigns D1, D2, ..."""

    filename: str
    media_type: str
    byte_length: int
    sha256: str
    page_count: int
    text_character_count: int
    textless_page_count: int
    pages: tuple[str, ...]
    original_pdf: bytes


@dataclass(frozen=True)
class SessionDocument:
    """Durable text-bearing PDF owned by exactly one research session."""

    document_id: str
    filename: str
    media_type: str
    byte_length: int
    sha256: str
    created_at: str
    page_count: int
    text_character_count: int
    textless_page_count: int
    pages: tuple[str, ...]
    original_pdf: bytes

    def __post_init__(self) -> None:
        if not DOCUMENT_ID.fullmatch(self.document_id) or not _consistent_document(self):
            raise ValueError("invalid_session_document")

    def __repr__(self) -> str:
        return (f"SessionDocument(document_id={self.document_id!r}, page_count={self.page_count}, "
                f"bytes={self.byte_length})")

    @property
    def extracted_text(self) -> str:
        """Canonical text: page extracts in order, with no inserted page labels."""
        return "".join(self.pages)

    @property
    def boundary_offsets(self) -> tuple[int, ...]:
        offsets = [0]
        for page in self.pages:
            offsets.append(offsets[-1] + len(page))
        return tuple(offsets)

    @property
    def interior_boundaries(self) -> tuple[int, ...]:
        """Offsets where a later page starts. These are not characters in the text."""
        return self.boundary_offsets[1:-1]


def sanitize_filename(name: object) -> str:
    """Display metadata only. Never a path, route, or storage key."""
    text = name if isinstance(name, str) else ""
    text = text.replace("\\", "/").split("/")[-1]
    text = "".join(ch for ch in text if ch.isprintable() and ch not in "\\/")
    text = " ".join(text.split()).strip(" .")
    if not text or text in {".", ".."}:
        return "document.pdf"
    if len(text) > MAX_FILENAME_LENGTH:
        suffix = ".pdf" if text.lower().endswith(".pdf") else ""
        text = text[:MAX_FILENAME_LENGTH - len(suffix)].rstrip(" .") + suffix
    return text or "document.pdf"


def content_disposition(filename: str) -> str:
    """Inline PDF disposition with a sanitized filename and no header injection."""
    cleaned = sanitize_filename(filename)
    ascii_name = "".join(ch if 32 <= ord(ch) < 127 and ch not in "\"\\<>" else "_" for ch in cleaned)
    if not ascii_name.strip("._"):
        ascii_name = "document.pdf"
    return f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(cleaned, safe='')}"


def textless_page_warning(count: int) -> str:
    if count <= 0:
        return ""
    noun = "page" if count == 1 else "pages"
    return f"{count} {noun} contained no extractable text."


def safe_original_href(href: str) -> bool:
    return bool(_ORIGINAL_HREF.fullmatch(href))


def _pdf_signal(filename: str, media_type: str) -> bool:
    media = media_type.lower().split(";", 1)[0].strip()
    return filename.lower().endswith(".pdf") or media == "application/pdf"


def _page_number(document: SessionDocument, offset: int) -> int:
    """1-based PDF page index containing this extracted-text offset."""
    return bisect_right(document.boundary_offsets, offset)


def page_slices(document: SessionDocument, start: int, end: int) -> list[tuple[int, int]]:
    """Split a half-open character range so no slice crosses a page boundary."""
    offsets = document.boundary_offsets
    slices = []
    cursor = start
    while cursor < end:
        page = _page_number(document, cursor)
        stop = min(end, offsets[page])
        if stop <= cursor:
            break
        slices.append((cursor, stop))
        cursor = stop
    return slices


def document_text_view(document: SessionDocument, start: int, end: int) -> Evidence:
    """One exact single-page slice of the retained extraction."""
    text = document.extracted_text
    if (not 0 <= start < end <= len(text) or end - start > TARGETED_SOURCE_CHARACTERS
            or _page_number(document, start) != _page_number(document, end - 1)):
        raise ValueError("invalid_source_range")
    page = _page_number(document, start)
    return Evidence(
        f"{document.document_id}@{start}:{end}", "", document.filename, text[start:end],
        "targeted_view", document.document_id, document.document_id, start, end,
        "user_document", document.document_id, document.filename, page, page,
        False, document.textless_page_count,
    )


def document_views(document: SessionDocument, start: int, end: int) -> list[Evidence]:
    """Exact slices covering [start, end), split on pages and the targeted-view bound."""
    if not 0 <= start < end <= len(document.extracted_text):
        raise ValueError("invalid_source_range")
    views = []
    for slice_start, slice_end in page_slices(document, start, end):
        for left in range(slice_start, slice_end, TARGETED_SOURCE_CHARACTERS):
            views.append(document_text_view(document, left, min(left + TARGETED_SOURCE_CHARACTERS, slice_end)))
    if not views:
        raise ValueError("invalid_source_range")
    return views


def index_parent(document: SessionDocument) -> Evidence:
    """In-memory locator parent. It is not an acquisition and is not model context."""
    return Evidence(
        document.document_id, "", document.filename, document.extracted_text, "fetched_source",
        document.document_id, None, None, None, "user_document", document.document_id,
        document.filename, None, None, False, document.textless_page_count,
    )


def _consistent_document(document: SessionDocument | PreparedDocument) -> bool:
    pages = document.pages
    extracted = "".join(pages)
    textless = sum(not page.strip() for page in pages)
    return bool(
        isinstance(document.original_pdf, bytes)
        and document.media_type == "application/pdf"
        and document.filename == sanitize_filename(document.filename)
        and document.filename
        and document.byte_length == len(document.original_pdf)
        and document.sha256 == hashlib.sha256(document.original_pdf).hexdigest()
        and len(document.sha256) == 64
        and document.page_count == len(pages) >= 1
        and all(isinstance(page, str) for page in pages)
        and document.text_character_count == len(extracted) <= MAX_EXTRACTED_CHARACTERS
        and document.textless_page_count == textless
        and textless < len(pages)
        and extracted.strip()
        and document.byte_length <= MAX_PDF_BYTES
        and document.page_count <= MAX_PDF_PAGES
    )


def _reject_malformed() -> None:
    raise DocumentRejected("pdf_malformed")


def prepare_pdf(filename: object, media_type: object, data: object) -> PreparedDocument:
    """Parse one PDF from memory. Failures use fixed codes and do not keep temp files."""
    if not isinstance(data, bytes) or isinstance(data, bool):
        raise DocumentRejected("pdf_malformed")
    supplied_name = filename if isinstance(filename, str) else ""
    supplied_type = media_type if isinstance(media_type, str) else ""
    if not supplied_name.strip():
        raise DocumentRejected("pdf_required")
    if not _pdf_signal(supplied_name, supplied_type):
        raise DocumentRejected("pdf_type_rejected")
    if len(data) > MAX_PDF_BYTES:
        raise DocumentRejected("pdf_too_large")
    if not data.startswith(b"%PDF-"):
        _reject_malformed()
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            try:
                opened = reader.decrypt("")
            except Exception:
                raise DocumentRejected("pdf_encrypted") from None
            if not opened:
                raise DocumentRejected("pdf_encrypted")
        page_count = len(reader.pages)
        if page_count > MAX_PDF_PAGES:
            raise DocumentRejected("pdf_too_many_pages")
        if page_count < 1:
            _reject_malformed()
        pages = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted is None:
                extracted = ""
            if not isinstance(extracted, str):
                _reject_malformed()
            pages.append(extracted)
            if sum(len(item) for item in pages) > MAX_EXTRACTED_CHARACTERS:
                raise DocumentRejected("pdf_too_much_text")
    except DocumentRejected:
        raise
    except (PdfReadError, FileNotDecryptedError, ValueError, TypeError, KeyError, IndexError, AssertionError):
        raise DocumentRejected("pdf_malformed") from None
    except Exception:
        # Parser internals, paths, and dependency errors stay inside this boundary.
        raise DocumentRejected("pdf_malformed") from None
    if not any(page.strip() for page in pages):
        raise DocumentRejected("pdf_no_text")
    prepared = PreparedDocument(
        sanitize_filename(supplied_name), "application/pdf", len(data),
        hashlib.sha256(data).hexdigest(), len(pages), sum(len(page) for page in pages),
        sum(not page.strip() for page in pages), tuple(pages), data,
    )
    if not _consistent_document(prepared):
        _reject_malformed()
    return prepared
