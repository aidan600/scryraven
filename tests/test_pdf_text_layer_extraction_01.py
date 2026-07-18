"""Offline PDF text-layer unit coverage and retired-local-opener guard."""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter

from core.pdf_text_layer_extraction import (
    PDF_TEXT_EXTRACTION_STATUS_EXTRACTED,
    PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER,
    PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED,
    extract_pdf_text_layer,
)
from proplex import mvp_single_relation_live_dogfood_run as dogfood


def test_generic_pdf_text_layer_adapter_extracts_sanitized_text() -> None:
    result = extract_pdf_text_layer(
        _tiny_text_pdf_bytes("Example County small claims filing fee is $54.")
    )

    assert result.status == PDF_TEXT_EXTRACTION_STATUS_EXTRACTED
    assert result.sanitized_text == "Example County small claims filing fee is $54."
    assert result.char_count == len(result.sanitized_text)
    assert result.page_count == 1
    assert result.raw_pdf_bytes_retained is False
    assert result.raw_pdf_text_retained is False
    assert result.ocr_opened is False
    assert result.browser_automation_opened is False
    assert result.external_service_used is False


def test_generic_pdf_text_layer_adapter_reports_no_text_layer() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    out = BytesIO()
    writer.write(out)

    result = extract_pdf_text_layer(out.getvalue())

    assert result.status == PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER
    assert result.sanitized_text == ""
    assert result.page_count == 1
    assert result.raw_pdf_bytes_retained is False
    assert result.ocr_opened is False


def test_generic_pdf_text_layer_adapter_reports_parse_failed() -> None:
    result = extract_pdf_text_layer(b"%PDF-1.4\nnot a valid xref\n%%EOF")

    assert result.status == PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED
    assert result.sanitized_text == ""
    assert result.raw_pdf_bytes_retained is False
    assert result.browser_automation_opened is False


def test_fetch_public_url_once_is_a_typed_fail_closed_retired_surface() -> None:
    with pytest.raises(dogfood.GenericSingleRelationLiveDogfoodRunError) as exc_info:
        dogfood.fetch_public_url_once("https://public.example/current-fee.pdf")

    exc = exc_info.value
    assert (
        exc.blocker
        == dogfood.BLOCKED_GENERIC_SINGLE_RELATION_LIVE_FETCH_READ_ENTRYPOINT_MISSING
    )
    assert exc.fetch_status_class == dogfood.FETCH_READ_UNKNOWN
    assert exc.fetch_content_type == dogfood.FETCH_READ_UNKNOWN
    assert exc.fetch_readable_text_obtained is False
    assert "local webpage fetch/read opener is retired" in str(exc)


def _tiny_text_pdf_bytes(text: str) -> bytes:
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET".encode("ascii"))
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
