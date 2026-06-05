from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

from core.document_review import build_document_review_context
from core.project_sources import (
    DEFAULT_VALIDATION_POSTURE,
    create_project,
    list_project_sources,
    load_project_source,
    load_source_record,
    load_source_revision,
    remove_project_source,
)
from ui.pages_projects import (
    format_project_row,
    format_project_source_row,
    project_select_options,
    project_source_boundary_caption,
    save_document_review_to_project,
    summarize_source_obligations,
)


def _clock() -> datetime:
    return datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _later_clock() -> datetime:
    return datetime(2026, 6, 5, 12, 5, tzinfo=timezone.utc)


def _ids():
    values = iter(("proj_ui", "src_ui", "rev_ui", "psrc_ui"))

    def factory(prefix: str) -> str:
        return next(values)

    return factory


def test_project_row_and_select_options_formatting(tmp_path: Path) -> None:
    project = create_project(
        "UI Vault",
        description="Local project sources",
        storage_root=tmp_path,
        clock=_clock,
        id_factory=_ids(),
    )

    assert format_project_row(project) == {
        "Name": "UI Vault",
        "Project ID": "proj_ui",
        "Description": "Local project sources",
        "Sources": 0,
        "Privacy": "local-private",
        "Retention": "active",
        "Created": "2026-06-05T12:00:00+00:00",
        "Updated": "2026-06-05T12:00:00+00:00",
    }
    assert project_select_options((project,)) == {"UI Vault (proj_ui)": "proj_ui"}


def test_project_source_row_and_obligation_summary_formatting(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("UI Sources", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = build_document_review_context(
        "# Memo\n\nThe current official API price is $20 and must be confirmed by June 30, 2026.",
        created_at=_clock(),
    )
    promoted = save_document_review_to_project(
        project,
        context,
        storage_root=tmp_path,
        title="Saved API memo",
    )

    summary = summarize_source_obligations(promoted.project_source)
    assert "findings:" in summary
    assert "obligations:" in summary
    assert f"validation posture: {DEFAULT_VALIDATION_POSTURE}" in summary

    row = format_project_source_row(promoted.project_source)
    assert row["Title"] == "Saved API memo"
    assert row["Project Source ID"] == promoted.project_source.project_source_id
    assert row["Source kind"] == "document-review-markdown"
    assert row["Evidence role"] == "document-local-evidence"
    assert row["Validation posture"] == DEFAULT_VALIDATION_POSTURE
    assert row["Input format"] == "markdown"
    assert row["Retention"] == "active"
    assert row["Raw text persisted"] is False
    assert row["Privacy"] == "local-private"


def test_save_document_review_to_project_uses_manifest_helpers_without_raw_text(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Save Helper", storage_root=tmp_path, clock=_clock, id_factory=ids)
    raw_document = "# Private memo\n\n" + ("Alpha private detail. " * 80) + "NEVER_STORE_THIS_FULL_TAIL"
    context = build_document_review_context(raw_document, created_at=_clock())

    promoted = save_document_review_to_project(project, context, storage_root=tmp_path)

    assert promoted.project.project_source_ids == (promoted.project_source.project_source_id,)
    assert list_project_sources(promoted.project, storage_root=tmp_path) == (promoted.project_source,)
    assert (
        load_project_source(promoted.project_source.project_source_id, storage_root=tmp_path) == promoted.project_source
    )
    assert (
        load_source_record(promoted.source_record.source_record_id, storage_root=tmp_path).retention_state == "active"
    )
    assert (
        load_source_revision(promoted.source_revision.source_revision_id, storage_root=tmp_path).raw_text_persisted
        is False
    )
    combined_manifests = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json"))
    assert context.normalized_text not in combined_manifests
    assert "NEVER_STORE_THIS_FULL_TAIL" not in combined_manifests
    assert '"raw_text_persisted": false' in combined_manifests


def test_remove_from_project_row_behavior_preserves_source_manifests(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Remove UI", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = build_document_review_context("# Memo\n\nA filing is due by June 30, 2026.", created_at=_clock())
    promoted = save_document_review_to_project(project, context, storage_root=tmp_path)

    updated = remove_project_source(
        promoted.project, promoted.project_source.project_source_id, storage_root=tmp_path, clock=_later_clock
    )
    removed = load_project_source(promoted.project_source.project_source_id, storage_root=tmp_path)

    assert updated.project_source_ids == ()
    assert format_project_source_row(removed)["Retention"] == "removed-from-project"
    assert (
        load_source_record(promoted.source_record.source_record_id, storage_root=tmp_path).retention_state == "active"
    )
    assert (
        load_source_revision(promoted.source_revision.source_revision_id, storage_root=tmp_path).retention_state
        == "active"
    )


def test_boundary_caption_names_closed_surfaces() -> None:
    caption = project_source_boundary_caption()
    assert "Local/private manifests" in caption
    assert "Raw normalized document text is not persisted by default" in caption
    assert "not public validation" in caption
    assert "No retrieval integration yet" in caption
    assert "No connectors" in caption
    assert "Project Instructions" in caption
    assert "snapshots" in caption
    assert "generated artifacts" in caption
    assert "not Project Sources or primary evidence" in caption


def test_pages_projects_has_no_closed_surface_imports() -> None:
    module = ast.parse(Path("ui/pages_projects.py").read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden = {
        "core.pipeline_orchestrator",
        "core.pipeline",
        "core.prompts",
        "core.llm",
        "core.search_providers",
        "core.retrieval",
        "core.storage",
        "core.db",
        "core.run_logging",
        "core.cache",
        "core.connectors",
    }
    assert imported_modules.isdisjoint(forbidden)
