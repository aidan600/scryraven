from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from core.document_review import (
    BOUNDARY_NOTICE,
    DOCUMENT_LOCAL_EVIDENCE_LABEL,
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
    assert a.metadata.version == "ag83b-v1"
    assert a.metadata.privacy_marker == PRIVACY_MARKER


def test_chunks_are_document_local_evidence_packets_with_anchors() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)

    assert context.chunks
    for chunk in context.chunks:
        assert chunk.document_id == context.metadata.document_id
        assert chunk.chunk_id.startswith(f"{context.metadata.document_id}-c")
        assert chunk.anchor_ids
        assert chunk.evidence_label == DOCUMENT_LOCAL_EVIDENCE_LABEL
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
    assert all("document-local-only" in hit.labels for hit in hits)


def test_markdown_export_preserves_privacy_boundary_labels_and_anchors() -> None:
    context = build_document_review_context(SAMPLE_MARKDOWN)
    export = context.export_markdown

    assert "Based only on the provided document" in export
    assert "Private/session-local" in export
    assert context.metadata.document_id in export
    assert "external-validation-required" in export
    assert "source-bound-numeric" in export
    assert "unsupported-by-document" in export
    assert "`s03-p001`" in export or "`s03-p002`" in export


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
    assert orchestrator_status.stdout.strip() == ""
