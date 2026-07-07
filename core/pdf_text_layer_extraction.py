"""Generic PDF text-layer extraction for fetch/read.

This adapter is deliberately narrow: it uses the existing pypdf dependency,
extracts text-layer text only, normalizes it, and returns safe diagnostics. It
does not OCR, render, call browsers, call services, or retain raw bytes/text.
"""

from __future__ import annotations

import importlib.util
import io
import re
from dataclasses import dataclass
from typing import Any

from core.document_review import normalize_document_text

PDF_TEXT_EXTRACTION_STATUS_EXTRACTED = "extracted"
PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER = "no_text_layer"
PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED = "parse_failed"
PDF_TEXT_EXTRACTION_STATUS_CAP_EXHAUSTED = "cap_exhausted"
PDF_TEXT_EXTRACTION_STATUSES = frozenset(
    {
        PDF_TEXT_EXTRACTION_STATUS_EXTRACTED,
        PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER,
        PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED,
        PDF_TEXT_EXTRACTION_STATUS_CAP_EXHAUSTED,
    }
)


@dataclass(frozen=True, slots=True)
class PdfTextLayerExtractionResult:
    """Safe result from a transient PDF text-layer parse."""

    status: str
    sanitized_text: str = ""
    char_count: int = 0
    page_count: int | None = None
    parser_name: str = "pypdf"
    raw_pdf_bytes_retained: bool = False
    raw_pdf_text_retained: bool = False
    ocr_opened: bool = False
    browser_automation_opened: bool = False
    external_service_used: bool = False

    @property
    def extracted(self) -> bool:
        return self.status == PDF_TEXT_EXTRACTION_STATUS_EXTRACTED

    def to_diagnostics(self) -> dict[str, Any]:
        return {
            "pdf_text_extraction_attempted": True,
            "pdf_text_extraction_status": self.status,
            "pdf_text_extraction_char_count": self.char_count,
            "pdf_text_extraction_page_count": self.page_count,
            "raw_pdf_bytes_retained": self.raw_pdf_bytes_retained,
            "raw_pdf_text_retained": self.raw_pdf_text_retained,
            "ocr_opened": self.ocr_opened,
            "browser_automation_opened": self.browser_automation_opened,
            "external_service_used": self.external_service_used,
        }


def extract_pdf_text_layer(pdf_bytes: bytes) -> PdfTextLayerExtractionResult:
    """Extract normalized text-layer text from PDF bytes without OCR."""

    if importlib.util.find_spec("pypdf") is None:
        fallback = _extract_pdf_literal_text_layer(pdf_bytes)
        if fallback.extracted:
            return fallback
        return PdfTextLayerExtractionResult(
            status=PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED,
        )
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
        page_count = len(reader.pages)
        page_texts: list[str] = []
        for page in reader.pages:
            normalized = normalize_document_text(page.extract_text() or "")
            if normalized:
                page_texts.append(normalized)
    except Exception:
        fallback = _extract_pdf_literal_text_layer(pdf_bytes)
        if fallback.extracted:
            return fallback
        return PdfTextLayerExtractionResult(
            status=PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED,
        )

    sanitized_text = " ".join("\n\n".join(page_texts).split())
    if not sanitized_text:
        return PdfTextLayerExtractionResult(
            status=PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER,
            page_count=page_count,
        )
    return PdfTextLayerExtractionResult(
        status=PDF_TEXT_EXTRACTION_STATUS_EXTRACTED,
        sanitized_text=sanitized_text,
        char_count=len(sanitized_text),
        page_count=page_count,
    )


def _extract_pdf_literal_text_layer(pdf_bytes: bytes) -> PdfTextLayerExtractionResult:
    """Best-effort text-layer fallback for simple literal-string PDF streams."""

    if not pdf_bytes.startswith(b"%PDF-"):
        return PdfTextLayerExtractionResult(
            status=PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED,
        )
    literals = [
        _decode_pdf_literal_string(match.group(1))
        for match in re.finditer(rb"\(((?:\\.|[^\\()])*)\)\s*Tj\b", pdf_bytes)
    ]
    sanitized_text = " ".join(
        "\n\n".join(
            normalize_document_text(item)
            for item in literals
            if normalize_document_text(item)
        ).split()
    )
    if not sanitized_text:
        return PdfTextLayerExtractionResult(
            status=PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED,
        )
    page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)) or None
    return PdfTextLayerExtractionResult(
        status=PDF_TEXT_EXTRACTION_STATUS_EXTRACTED,
        sanitized_text=sanitized_text,
        char_count=len(sanitized_text),
        page_count=page_count,
        parser_name="pdf_literal_text_layer",
    )


def _decode_pdf_literal_string(value: bytes) -> str:
    out = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char != 0x5C:
            out.append(char)
            index += 1
            continue
        index += 1
        if index >= len(value):
            break
        escaped = value[index]
        index += 1
        if escaped in b"nrtbf":
            out.extend(
                {
                    ord("n"): b"\n",
                    ord("r"): b"\r",
                    ord("t"): b"\t",
                    ord("b"): b"\b",
                    ord("f"): b"\f",
                }[escaped]
            )
            continue
        if 48 <= escaped <= 55:
            digits = bytes([escaped])
            while index < len(value) and len(digits) < 3 and 48 <= value[index] <= 55:
                digits += bytes([value[index]])
                index += 1
            out.append(int(digits, 8) & 0xFF)
            continue
        out.append(escaped)
    return out.decode("latin-1", errors="ignore")


__all__ = [
    "PDF_TEXT_EXTRACTION_STATUS_CAP_EXHAUSTED",
    "PDF_TEXT_EXTRACTION_STATUS_EXTRACTED",
    "PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER",
    "PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED",
    "PDF_TEXT_EXTRACTION_STATUSES",
    "PdfTextLayerExtractionResult",
    "extract_pdf_text_layer",
]
