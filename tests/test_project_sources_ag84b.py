from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from pathlib import Path

from core.document_review import build_document_review_context
from core.project_sources import (
    DEFAULT_PROJECT_SOURCE_STORAGE_ROOT,
    DEFAULT_VALIDATION_POSTURE,
    LOCAL_PRIVATE_BOUNDARY_MARKER,
    PROJECT_SOURCE_GENERATOR,
    PROJECT_SOURCE_SCHEMA_VERSION,
    add_project_source_from_document_review,
    create_project,
    list_project_sources,
    list_projects,
    load_project,
    load_project_source,
    load_source_record,
    load_source_revision,
    remove_project_source,
)


def _clock() -> datetime:
    return datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)


def _later_clock() -> datetime:
    return datetime(2026, 6, 5, 12, 5, tzinfo=timezone.utc)


def _ids() -> callable:
    counters: dict[str, int] = {}

    def make(prefix: str) -> str:
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}_fixed_{counters[prefix]:02d}"

    return make


def test_create_project_manifest_schema_timestamps_and_listing(tmp_path: Path) -> None:
    ids = _ids()

    project = create_project(
        "Research Vault",
        description="Local-only sources",
        storage_root=tmp_path,
        clock=_clock,
        id_factory=ids,
    )

    assert project.project_id == "proj_fixed_01"
    assert project.schema_version == PROJECT_SOURCE_SCHEMA_VERSION
    assert project.created_at == "2026-06-05T12:00:00+00:00"
    assert project.updated_at == "2026-06-05T12:00:00+00:00"
    assert project.privacy_class == "local-private"
    assert project.retention_state == "active"
    assert project.project_source_ids == ()
    assert project.manifest_metadata is not None
    assert project.manifest_metadata.generator == PROJECT_SOURCE_GENERATOR
    assert project.manifest_metadata.local_private_boundary == LOCAL_PRIVATE_BOUNDARY_MARKER

    payload = json.loads((tmp_path / "projects" / "proj_fixed_01.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == PROJECT_SOURCE_SCHEMA_VERSION
    assert payload["manifest_metadata"]["managed_copy_policy"] == "raw-source-files-not-copied-by-default"
    assert list_projects(storage_root=tmp_path) == (project,)
    assert load_project(project.project_id, storage_root=tmp_path) == project


def test_add_document_review_project_source_preserves_compact_metadata(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Claims", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = build_document_review_context(
        """
# Evidence memo

The current API pricing is $20 per seat according to Table 1.
Legal compliance requires filing by June 30, 2026.
Clinical efficacy improved according to the study.
The benchmark paper reports 91% accuracy.
Internal records show 14 affected customers.
""",
        title="Evidence memo",
        created_at=_clock(),
    )

    result = add_project_source_from_document_review(
        project,
        context,
        storage_root=tmp_path,
        clock=_later_clock,
        id_factory=ids,
    )

    assert result.project.project_source_ids == ("psrc_fixed_01",)
    assert result.project_source.project_id == project.project_id
    assert result.project_source.source_record_id == "src_fixed_01"
    assert result.project_source.source_revision_id == "rev_fixed_01"
    assert result.project_source.title == "Evidence memo"
    assert result.project_source.source_kind == "document-review-markdown"
    assert result.project_source.scope == "project-source"
    assert result.project_source.privacy_class == "local-private"
    assert result.project_source.evidence_role == "document-local-evidence"
    assert result.project_source.validation_posture == DEFAULT_VALIDATION_POSTURE
    assert result.project_source.raw_text_persisted is False
    assert result.project_source.source_identity["document_id"] == context.metadata.document_id
    assert result.project_source.source_identity["document_hash"] == context.metadata.document_hash
    assert result.project_source.source_identity["input_format"] == "markdown"
    assert result.project_source.parser_metadata["parser_name"] == "text-normalizer"
    assert result.project_source.parser_metadata["parser_version"] == context.metadata.parser_version
    assert result.project_source.parser_metadata["parser_confidence"] == context.metadata.parser_confidence
    assert result.project_source.parser_metadata["parser_notes"] == list(context.metadata.parser_notes)

    revision = result.source_revision
    assert revision.document_hash == context.metadata.document_hash
    assert revision.parser_metadata == result.project_source.parser_metadata
    assert revision.raw_text_persisted is False
    assert revision.local_private_boundary == LOCAL_PRIVATE_BOUNDARY_MARKER
    assert {item["anchor_id"] for item in revision.anchor_manifest} == {anchor.anchor_id for anchor in context.anchors}
    assert {item["chunk_id"] for item in revision.chunk_manifest} == {chunk.chunk_id for chunk in context.chunks}
    assert all("text" not in item for item in revision.chunk_manifest)
    assert all("text_preview" in item and "source_reference" in item for item in revision.anchor_manifest)
    assert all("labels" in item and "source_obligation" in item for item in revision.finding_manifest)
    assert all("text" not in item for item in revision.finding_manifest)

    summary = result.project_source.source_obligation_summary
    assert summary["finding_count"] == len(context.findings)
    assert summary["validation_posture"] == DEFAULT_VALIDATION_POSTURE
    assert summary["label_counts"]["external-validation-required"] >= 1
    assert summary["label_counts"]["official-current-source-needed"] >= 1
    assert summary["obligation_counts"]["legal-current-official-source-needed"] >= 1
    assert summary["obligation_counts"]["medical-scientific-validation-required"] >= 1
    assert summary["obligation_counts"]["academic-source-needed"] >= 1
    assert summary["obligation_counts"]["corpus-validation-required"] >= 1
    assert summary["evidence_role_counts"]
    assert summary["validation_need_counts"]
    assert summary["risk_level_counts"]

    assert list_project_sources(result.project, storage_root=tmp_path) == (result.project_source,)
    assert load_project_source("psrc_fixed_01", storage_root=tmp_path) == result.project_source
    assert load_source_record("src_fixed_01", storage_root=tmp_path) == result.source_record
    assert load_source_revision("rev_fixed_01", storage_root=tmp_path) == result.source_revision


def test_remove_project_source_removes_membership_only(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Remove demo", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = build_document_review_context("# Memo\n\nA required filing is due by June 30, 2026.", created_at=_clock())
    promoted = add_project_source_from_document_review(
        project, context, storage_root=tmp_path, clock=_clock, id_factory=ids
    )

    updated = remove_project_source(promoted.project, "psrc_fixed_01", storage_root=tmp_path, clock=_later_clock)

    assert updated.project_source_ids == ()
    assert updated.updated_at == "2026-06-05T12:05:00+00:00"
    assert load_project(updated.project_id, storage_root=tmp_path).project_source_ids == ()
    assert load_project_source("psrc_fixed_01", storage_root=tmp_path).retention_state == "active"
    assert load_source_revision("rev_fixed_01", storage_root=tmp_path).retention_state == "active"


def test_compact_manifests_do_not_persist_normalized_raw_document_text(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Privacy", storage_root=tmp_path, clock=_clock, id_factory=ids)
    raw_document = "# Private memo\n\n" + "Alpha private detail. " * 80 + "NEVER_PERSIST_FULL_RAW_DOCUMENT_TAIL"
    context = build_document_review_context(raw_document, created_at=_clock())

    add_project_source_from_document_review(project, context, storage_root=tmp_path, clock=_clock, id_factory=ids)

    combined_manifests = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.json"))
    assert context.normalized_text not in combined_manifests
    assert "NEVER_PERSIST_FULL_RAW_DOCUMENT_TAIL" not in combined_manifests
    assert '"raw_text_persisted": false' in combined_manifests
    assert "raw-source-files-not-copied-by-default" in combined_manifests


def test_default_storage_root_is_ignored_output_project_sources() -> None:
    assert DEFAULT_PROJECT_SOURCE_STORAGE_ROOT == Path("output/project_sources")


def test_project_sources_module_has_no_closed_surface_imports() -> None:
    module = ast.parse(Path("core/project_sources.py").read_text(encoding="utf-8"))
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
    }
    assert imported_modules.isdisjoint(forbidden)


def test_project_source_manifests_use_only_manifest_directories(tmp_path: Path) -> None:
    ids = _ids()
    project = create_project("Paths", storage_root=tmp_path, clock=_clock, id_factory=ids)
    context = build_document_review_context(
        "# Memo\n\nThe project will reduce review time by 25%.", created_at=_clock()
    )

    add_project_source_from_document_review(project, context, storage_root=tmp_path, clock=_clock, id_factory=ids)

    relative_dirs = {path.relative_to(tmp_path).parts[0] for path in tmp_path.rglob("*.json")}
    assert relative_dirs == {"projects", "project_sources", "source_records", "source_revisions"}
