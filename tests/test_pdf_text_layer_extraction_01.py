"""PRODUCT-PATH-REGRESSION: generic fetch/read PDF text-layer adapter.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: proplex.mvp_single_relation_live_dogfood_run.fetch_public_url_once
Runtime consumer: proplex.mvp_single_relation_live_dogfood_run -> FetchReadContentPacket
Why ordinary product-path work cannot be done directly: offline validation must
not make live public fetches; fake opener responses exercise the same fetch/read
adapter and blocker path without network calls.
Integration deadline: current phase.
Exit condition: keep while fetch/read consumes generic PDF text-layer extraction,
or replace with broader product-path coverage if the fetch/read adapter moves.
Why this is not a shadow product path: tests call the production adapter and
public fetch/read function, not an alternate extraction or evidence path.
Forbidden interpretation: PDF extraction is not evidence admission, source
authority, source-obligation satisfaction, citation eligibility, FAP/Author
output, product correctness, OCR support, or live validation.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

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


def test_fetch_public_url_once_reads_pdf_looking_url_without_official_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dogfood,
        "build_opener",
        lambda _redirect_handler: _FakeOpener(
            _FakeResponse(
                _tiny_text_pdf_bytes("Independent public PDF states the fee is $54."),
                url="https://independent.example/current-fee.pdf",
                content_type="application/octet-stream",
            )
        ),
    )

    result = dogfood.fetch_public_url_once("https://independent.example/current-fee.pdf")

    assert result.content_type == "application/octet-stream"
    assert result.sanitized_text == "Independent public PDF states the fee is $54."
    assert result.pdf_text_extraction_attempted is True
    assert result.pdf_text_extraction_status == PDF_TEXT_EXTRACTION_STATUS_EXTRACTED
    assert result.pdf_text_extraction_page_count == 1
    assert result.raw_pdf_bytes_retained is False
    assert result.raw_pdf_text_retained is False
    assert result.bounded_text_retained is True
    assert result.ocr_opened is False
    assert result.browser_automation_opened is False
    assert result.external_service_used is False


def test_fetch_public_url_once_blocks_pdf_without_text_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    out = BytesIO()
    writer.write(out)
    monkeypatch.setattr(
        dogfood,
        "build_opener",
        lambda _redirect_handler: _FakeOpener(
            _FakeResponse(
                out.getvalue(),
                url="https://example.gov/blank.pdf",
                content_type="application/pdf",
            )
        ),
    )

    with pytest.raises(dogfood.GenericSingleRelationLiveDogfoodRunError) as exc_info:
        dogfood.fetch_public_url_once("https://example.gov/blank.pdf")

    exc = exc_info.value
    assert exc.blocker == dogfood.BLOCKED_FETCH_READ_PDF_TEXT_EXTRACTION_UNAVAILABLE
    assert exc.pdf_text_extraction_attempted is True
    assert exc.pdf_text_extraction_status == PDF_TEXT_EXTRACTION_STATUS_NO_TEXT_LAYER
    assert exc.pdf_text_extraction_page_count == 1
    assert exc.raw_pdf_bytes_retained is False
    assert exc.ocr_opened is False


def test_fetch_public_url_once_blocks_corrupt_pdf_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dogfood,
        "build_opener",
        lambda _redirect_handler: _FakeOpener(
            _FakeResponse(
                b"%PDF-1.4\nnot a valid xref\n%%EOF",
                url="https://example.gov/corrupt.pdf",
                content_type="application/pdf",
            )
        ),
    )

    with pytest.raises(dogfood.GenericSingleRelationLiveDogfoodRunError) as exc_info:
        dogfood.fetch_public_url_once("https://example.gov/corrupt.pdf")

    exc = exc_info.value
    assert exc.blocker == dogfood.BLOCKED_FETCH_READ_PDF_TEXT_EXTRACTION_FAILED
    assert exc.pdf_text_extraction_attempted is True
    assert exc.pdf_text_extraction_status == PDF_TEXT_EXTRACTION_STATUS_PARSE_FAILED
    assert exc.raw_pdf_text_retained is False
    assert exc.browser_automation_opened is False
    assert exc.external_service_used is False


class _FakeHeaders(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str:
        return super().get(key.lower(), default or "")


class _FakeResponse:
    def __init__(self, body: bytes, *, url: str, content_type: str) -> None:
        self._body = body
        self._url = url
        self.status = 200
        self.headers = _FakeHeaders({"content-type": content_type})

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url


class _FakeOpener:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def open(self, _request: Any, *, timeout: int) -> _FakeResponse:
        assert timeout == 20
        return self._response


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
