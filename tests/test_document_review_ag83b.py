from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.document_review import (
    BOUNDARY_NOTICE,
    DOCUMENT_LOCAL_EVIDENCE_LABEL,
    DOCUMENT_LOCAL_ONLY_LABEL,
    DOCUMENT_SOURCE_SCOPE,
    FOLLOWUP_RETRIEVAL_MODE,
    PRIVACY_MARKER,
    build_document_review_context,
    normalize_document_text,
    retrieve_document_followup,
)

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_REVIEW_HELPER_PATHS = [
    ROOT / "core" / "document_review.py",
    ROOT / "ui" / "pages_document_review.py",
]
FORBIDDEN_IMPORTS = {
    "core.llm",
    "core.pipeline",
    "core.pipeline_orchestrator",
    "core.prompts",
    "core.retrieval",
    "core.search",
    "core.search_providers",
    "core.providers",
    "core.models",
    "core.cache",
    "core.storage",
    "core.db",
    "sqlite3",
    "requests",
    "httpx",
    "urllib.request",
}
FORBIDDEN_CALL_NAMES = {
    "ask_model",
    "compute_similarities",
    "embed_texts",
    "fetch_linkup_precision_block",
    "filter_top_evidence",
    "process_search_queries",
    "run_economist_step",
    "run_pipeline",
    "run_scout",
    "save_session",
    "configure_storage",
    "open",
}
PERSISTENCE_TERMS = {
    "jsonl",
    "sqlite",
    "cache/",
    "execution_log",
    "app.log",
    "full_trace",
    "provider_payload",
}

SAMPLE_MARKDOWN = """
# Launch Plan

The project will reduce review time by 25% according to Table 1.

## Risks

- Current vendor pricing may increase by 12% before renewal.
- Therefore, the team should request legal review by June 30, 2026.

| Owner | Task |
| --- | --- |
| Mina | Prepare rollout checklist |
"""


def test_parser_builds_sections_anchors_lists_and_tables() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN, title="Launch review")

    assert context.metadata.title == "Launch review"
    assert context.metadata.input_format == "markdown"
    assert [section.heading for section in context.sections] == ["Document", "Launch Plan", "Risks"]
    assert any(anchor.kind == "list" for anchor in context.anchors)
    assert any(anchor.kind == "table" for anchor in context.anchors)
    assert {anchor.anchor_id for anchor in context.anchors} >= {"s02-p001", "s03-p001", "s03-p002"}
    assert all(anchor.extraction_confidence > 0 for anchor in context.anchors)


def test_document_id_and_hash_are_stable_for_normalized_text() -> None:
    a = build_document_review_context("\n\r\n# Memo\r\n\r\nA deadline is 2026.\r\n")
    b = build_document_review_context("# Memo\n\nA deadline is 2026.")

    assert normalize_document_text("\n\r\n# Memo\r\n\r\nA deadline is 2026.\r\n") == "# Memo\n\nA deadline is 2026."
    assert a.metadata.document_id == b.metadata.document_id
    assert a.metadata.document_hash == b.metadata.document_hash
    assert a.metadata.version == "ag83d-ag83c-v1"
    assert a.metadata.privacy_marker == PRIVACY_MARKER


def test_chunks_are_document_local_evidence_packets_with_anchors() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)

    assert context.chunks
    for chunk in context.chunks:
        assert chunk.document_id == context.metadata.document_id
        assert chunk.document_hash == context.metadata.document_hash
        assert chunk.chunk_id.startswith(f"{context.metadata.document_id}-c")
        assert chunk.anchor_ids
        assert chunk.evidence_label == DOCUMENT_LOCAL_EVIDENCE_LABEL
        assert chunk.locality_label == DOCUMENT_LOCAL_ONLY_LABEL
        assert chunk.source_scope == DOCUMENT_SOURCE_SCOPE
        assert chunk.retrieval_mode == FOLLOWUP_RETRIEVAL_MODE
        assert chunk.preview
        assert 0 < chunk.extraction_confidence <= 1


def test_review_findings_preserve_boundary_labels_and_numeric_source_labels() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)
    labels = {label for finding in context.findings for label in finding.labels}

    assert "source-bound-numeric" in labels
    assert "external-validation-required" in labels
    assert "document-supported-inference" in labels
    assert "unsupported-by-document" in labels
    assert context.boundary_notice == BOUNDARY_NOTICE
    assert all(finding.anchor_ids for finding in context.findings)


def test_ag83d_rich_claim_fields_and_source_obligations_are_deterministic() -> None:
    sample = """
# Evidence memo

The program reduces review time because the appendix compares baseline data.
The current API pricing is $20 per seat.
Legal compliance requires filing by June 30, 2026.
Clinical efficacy improved according to the study.
The benchmark paper reports 91% accuracy.
Internal records show 14 affected customers.
"""
    context = build_document_review_context(sample)
    labels = {label for finding in context.findings for label in finding.labels}
    obligations = {finding.source_obligation for finding in context.findings}
    claim_types = {finding.claim_type for finding in context.findings}

    assert "direct-document-statement" in labels
    assert "document-supported-inference" in labels
    assert "official-current-source-needed" in labels
    assert "legal-current-official-source-needed" in labels
    assert "financial-numeric-source-needed" in labels
    assert "medical-scientific-validation-required" in labels
    assert "academic-source-needed" in labels
    assert "product-api-current-technical-source-needed" in labels
    assert "corpus-validation-required" in labels
    assert "external-validation-required" in labels
    assert "source-bound-numeric" in labels
    assert "product-api-current-technical-source-needed" in obligations
    assert "legal-current-official-source-needed" in obligations
    assert "medical-scientific-validation-required" in obligations
    assert "academic-source-needed" in obligations
    assert "corpus-validation-required" in obligations
    assert "document-supported-inference" in claim_types
    assert all(finding.validation_need for finding in context.findings)
    assert all(finding.evidence_role for finding in context.findings)


def test_ag83d_support_cues_do_not_become_external_validation() -> None:
    context = build_document_review_context(
        "# Memo\n\nCurrent vendor pricing is $12 according to Table 1.\n\nCurrent vendor pricing is $15."
    )
    supported = next(finding for finding in context.findings if "$12" in finding.text)
    unsupported = next(finding for finding in context.findings if "$15" in finding.text)

    assert "unsupported-by-document" not in supported.labels
    assert supported.source_obligation == "official-current-source-needed"
    assert supported.validation_need == "official-current-if-validated"
    assert "external-validation-required" in supported.labels
    assert "unsupported-by-document" in unsupported.labels
    assert unsupported.evidence_role == "unsupported-by-document"
    assert "outside-world truth" in supported.note


def test_ag83d_action_obligation_deadline_opinion_and_risk_labels() -> None:
    context = build_document_review_context(
        "# Plan\n\nMina should request legal review by June 30, 2026 because vendor renewal may increase exposure."
    )
    finding = context.findings[0]

    assert "action-item-obligation" in finding.labels
    assert "date-deadline-claim" in finding.labels
    assert "opinion-recommendation" in finding.labels
    assert "risk-red-flag" in finding.labels
    assert finding.claim_type == "risk-red-flag"
    assert finding.risk_level == "medium"


def test_ag83d_possible_internal_tension_is_conservative_and_unresolved() -> None:
    context = build_document_review_context(
        "# Plan\n\nThe renewal fee is 10% for the pilot.\n\nThe renewal fee is 12% for the pilot."
    )
    tension = next(
        finding for finding in context.findings if finding.claim_type == "document-internal-possible-tension"
    )

    assert "document-internal-possible-tension" in tension.labels
    assert tension.evidence_role == "possible-tension"
    assert tension.risk_level == "medium"
    assert "no winner" in tension.note
    assert len(tension.anchor_ids) == 2


def test_ag83d_export_includes_rich_classification_fields_and_boundary() -> None:
    context = build_document_review_context("# Memo\n\nCurrent API pricing is $20 per seat.")
    export = context.export_markdown

    assert "Claim type:" in export
    assert "Source obligation:" in export
    assert "Evidence role:" in export
    assert "Validation need:" in export
    assert "Risk level:" in export
    assert "product-api-current-technical-source-needed" in export
    assert "official-current-source-needed" in export
    assert "No public web validation" in export


def test_context_snapshot_is_immutable_and_mutation_safe() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)
    snapshot = context.snapshot()

    assert snapshot == context
    with pytest.raises(FrozenInstanceError):
        snapshot.metadata.title = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snapshot.anchors += ()  # type: ignore[misc]


def test_followup_retrieval_returns_relevant_retained_chunks_only() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)

    hits = retrieve_document_followup(context, "legal review deadline renewal")

    assert hits
    assert hits[0].score > 0
    assert any("s03" in anchor for hit in hits for anchor in hit.anchor_ids)
    assert all(DOCUMENT_LOCAL_EVIDENCE_LABEL in hit.labels for hit in hits)
    assert all(DOCUMENT_LOCAL_ONLY_LABEL in hit.labels for hit in hits)
    assert all(DOCUMENT_SOURCE_SCOPE in hit.labels for hit in hits)
    assert all(hit.retrieval_mode == FOLLOWUP_RETRIEVAL_MODE for hit in hits)


def test_followup_retrieval_handles_multiple_queries_no_hits_and_stable_ordering() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)

    heading_hits = retrieve_document_followup(context, "Risks")
    keyword_hits = retrieve_document_followup(context, "rollout checklist")
    repeated_hits = retrieve_document_followup(context, "rollout checklist")
    no_hits = retrieve_document_followup(context, "astronomy nebula telescope")

    assert heading_hits
    assert heading_hits[0].section_heading == "Risks"
    assert keyword_hits
    assert keyword_hits == repeated_hits
    assert [hit.chunk_id for hit in keyword_hits] == sorted(
        [hit.chunk_id for hit in keyword_hits],
        key=lambda chunk_id: (-next(hit.score for hit in keyword_hits if hit.chunk_id == chunk_id), chunk_id),
    )
    assert no_hits == ()


def test_markdown_export_preserves_privacy_boundary_labels_and_anchors() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)
    export = context.export_markdown

    assert "Based only on the provided document" in export
    assert "Private/session-local" in export
    assert "Follow-up boundary" in export
    assert "not model-mediated natural-language Q&A" in export
    assert "no persistent document-library state" in export
    assert DOCUMENT_LOCAL_EVIDENCE_LABEL in export
    assert DOCUMENT_SOURCE_SCOPE in export
    assert context.metadata.document_id in export
    assert "external-validation-required" in export
    assert "source-bound-numeric" in export
    assert "unsupported-by-document" in export
    assert "`s03-p001`" in export or "`s03-p002`" in export


def test_anchor_line_references_are_normalized_lines_not_page_precision() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)

    first_paragraph = next(anchor for anchor in context.anchors if anchor.anchor_id == "s02-p001")
    risk_list = next(anchor for anchor in context.anchors if anchor.anchor_id == "s03-p001")
    risk_table = next(anchor for anchor in context.anchors if anchor.kind == "table")

    assert first_paragraph.line_reference == "line 3"
    assert risk_list.line_reference == "lines 7-8"
    assert risk_table.line_reference == "lines 10-12"
    assert first_paragraph.extraction_confidence == 0.82
    assert risk_list.extraction_confidence == 0.74
    assert risk_table.extraction_confidence == 0.62
    assert all("page" not in anchor.line_reference for anchor in context.anchors)


def test_anchor_ids_remain_deterministic_under_harmless_blank_line_normalization() -> None:
    compact = "# Memo\n\nA deadline is 2026.\n\n## Next\n\n- Owner prepares checklist.\n"
    padded = "\n\n# Memo\n\n\nA deadline is 2026.\n\n\n## Next\n\n- Owner prepares checklist.\n\n"

    compact_context = build_document_review_context(compact)
    padded_context = build_document_review_context(padded)

    assert [anchor.anchor_id for anchor in compact_context.anchors] == [
        anchor.anchor_id for anchor in padded_context.anchors
    ]
    assert [anchor.kind for anchor in compact_context.anchors] == [anchor.kind for anchor in padded_context.anchors]


def test_document_review_helpers_do_not_import_live_runtime_or_persistence_paths() -> None:
    for path in DOCUMENT_REVIEW_HELPER_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        assert imported_modules.isdisjoint(FORBIDDEN_IMPORTS), path


def test_document_review_helpers_do_not_call_live_or_persistence_functions() -> None:
    for path in DOCUMENT_REVIEW_HELPER_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        called_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_names.add(node.func.attr)

        assert called_names.isdisjoint(FORBIDDEN_CALL_NAMES), path


def test_document_review_helpers_do_not_reference_raw_text_persistence_surfaces() -> None:
    for path in DOCUMENT_REVIEW_HELPER_PATHS:
        text = path.read_text(encoding="utf-8").casefold()
        leaked_terms = {term for term in PERSISTENCE_TERMS if term in text}
        assert not leaked_terms, (path, leaked_terms)


def test_pipeline_orchestrator_remains_unchanged() -> None:
    orchestrator_status = __import__("subprocess").run(
        ["git", "diff", "--name-only", "--", "core/pipeline_orchestrator.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if orchestrator_status.stdout.strip():
        diff = __import__("subprocess").run(
            ["git", "diff", "--", "core/pipeline_orchestrator.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert (
            "final_answer_runtime_adapter" in diff
            or "FinalAnswerPacket" in diff
            or "pre_author_source_obligation_projection" in diff
            or "session_output_projection" in diff
        )


def test_ag83c_parser_abstraction_preserves_pasted_text_regression() -> None:
    from core.document_review import DocumentInput, build_document_review_context_from_input, parse_document_input

    parsed = parse_document_input(
        DocumentInput(content=SAMPLE_MARKDOWN, input_format="markdown", title="Launch review")
    )
    context = build_document_review_context_from_input(
        DocumentInput(content=SAMPLE_MARKDOWN, input_format="markdown", title="Launch review")
    )

    assert parsed.input_format == "markdown"
    assert parsed.parser_name == "text-normalizer"
    assert context.metadata.input_format == "markdown"
    assert context.metadata.parser_name == "text-normalizer"
    assert [anchor.anchor_id for anchor in context.anchors] == [
        anchor.anchor_id for anchor in build_document_review_context(SAMPLE_MARKDOWN, title="Launch review").anchors
    ]
    assert all(anchor.source_reference == anchor.line_reference for anchor in context.anchors)


def test_ag83c_pdf_parsing_uses_page_anchors_without_ocr_or_layout_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    from core.document_review import DocumentInput, build_document_review_context_from_input, parse_document_input

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakeReader:
        def __init__(self, _stream: object) -> None:
            self.pages = [
                FakePage("PDF memo\nThe current API pricing is $20 according to Table 1."),
                FakePage("The team should request legal review by June 30, 2026."),
            ]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=FakeReader))
    monkeypatch.setattr(
        "core.document_review.importlib.util.find_spec", lambda name: object() if name == "pypdf" else None
    )
    parsed = parse_document_input(DocumentInput(content=b"%PDF synthetic", input_format="pdf", title="PDF memo"))
    context = build_document_review_context_from_input(DocumentInput(content=b"%PDF synthetic", input_format="pdf"))

    assert parsed.input_format == "pdf"
    assert parsed.parser_name == "pypdf"
    assert "no OCR" in " ".join(parsed.notes)
    assert context.metadata.input_format == "pdf"
    assert context.metadata.parser_confidence <= 0.76
    assert {anchor.source_page_start for anchor in context.anchors} == {1, 2}
    assert all(anchor.source_reference.startswith("PDF page ") for anchor in context.anchors)
    assert all("layout coordinates" in anchor.anchor_note for anchor in context.anchors)
    assert "official-current-source-needed" in {label for finding in context.findings for label in finding.labels}
    assert "No public web validation" in context.export_markdown


def test_ag83c_docx_parsing_uses_structural_anchors_and_flattened_tables() -> None:
    import io
    import zipfile

    from core.document_review import DocumentInput, build_document_review_context_from_input, parse_document_input

    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>DOCX memo</w:t></w:r></w:p>
    <w:p><w:r><w:t>The current vendor pricing is $15 according to Table 1.</w:t></w:r></w:p>
    <w:tbl>
      <w:tr><w:tc><w:p><w:r><w:t>Owner</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Task</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>Mina</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Prepare review checklist</w:t></w:r></w:p></w:tc></w:tr>
    </w:tbl>
  </w:body>
</w:document>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    content = buffer.getvalue()
    parsed = parse_document_input(DocumentInput(content=content, input_format="docx", title="DOCX memo"))
    context = build_document_review_context_from_input(DocumentInput(content=content, input_format="docx"))

    assert parsed.input_format == "docx"
    assert parsed.parser_name == "stdlib-docx-xml"
    assert "# DOCX memo" in parsed.text
    assert "| Owner | Task |" in parsed.text
    assert context.metadata.input_format == "docx"
    assert [section.heading for section in context.sections] == ["Document", "DOCX memo"]
    assert any(anchor.kind == "table" for anchor in context.anchors)
    assert all(anchor.source_format == "docx" for anchor in context.anchors)
    assert all(anchor.source_reference.startswith("DOCX block ") for anchor in context.anchors)
    assert all(anchor.source_page_start is None for anchor in context.anchors)
    assert "rendered page" in " ".join(context.metadata.parser_notes)
    assert "no provider/model/search calls" in context.export_markdown


def test_ag83c_parsed_document_hash_is_stable_for_parsed_content() -> None:
    from core.document_review import DocumentInput, build_document_review_context_from_input

    first = build_document_review_context_from_input(
        DocumentInput(content="\n# Memo\n\nThe current API pricing is $20.\n", input_format="markdown")
    )
    second = build_document_review_context_from_input(
        DocumentInput(content="# Memo\n\nThe current API pricing is $20.", input_format="markdown")
    )

    assert first.metadata.document_hash == second.metadata.document_hash
    assert first.metadata.document_id == second.metadata.document_id
