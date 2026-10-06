"""Deterministic text PDFs. No private files, OCR, or image pipelines."""

from io import BytesIO

from pypdf import PdfReader, PdfWriter


def _literal(text: str) -> bytes:
    raw = text.encode("latin-1")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_pdf(pages: list[str]) -> bytes:
    """One WinAnsi text page per string. Empty strings are textless pages."""
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }
    next_id = 4
    page_ids = []
    for page in pages:
        stream = b"BT /F1 12 Tf 72 720 Td (" + _literal(page) + b") Tj ET"
        content_id = next_id
        next_id += 1
        page_id = next_id
        next_id += 1
        page_ids.append(page_id)
        objects[content_id] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
            b"/Resources << /Font << /F1 3 0 R >> >> >>" % content_id
        )
    kids = b" ".join(b"%d 0 R" % page_id for page_id in page_ids)
    objects[2] = b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % len(pages)
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number in range(1, next_id):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % next_id + b"0000000000 65535 f \n"
    for number in range(1, next_id):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (next_id, xref)
    return bytes(out)


def encrypted_pdf(pages: list[str], password: str = "secret") -> bytes:
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(text_pdf(pages))))
    writer.encrypt(password)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
