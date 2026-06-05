"""Local manifest-first Project Source helpers for AG-84B.

This module is intentionally pure/local. It creates schema-versioned Project and
ProjectSource manifests from document-review metadata without calling providers,
search, retrieval, prompts, caches, telemetry, SQLite, JSONL traces, or the
pipeline/orchestrator. It does not persist raw private document text by default.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

from core.document_review import (
    BOUNDARY_NOTICE,
    DOCUMENT_LOCAL_EVIDENCE_LABEL,
    DOCUMENT_SOURCE_SCOPE,
    PRIVACY_WARNING,
    DocumentReviewContext,
)

PROJECT_SOURCE_SCHEMA_VERSION = "ag84b-project-sources-v1"
PROJECT_SOURCE_GENERATOR = "scryraven-ag84b-project-sources"
DEFAULT_PROJECT_SOURCE_STORAGE_ROOT = Path("output/project_sources")
LOCAL_PRIVATE_BOUNDARY_MARKER = "local-private-project-source-manifest"
PROJECT_SCOPE = "project-source"
DEFAULT_PRIVACY_CLASS = "local-private"
DEFAULT_RETENTION_STATE = "active"
DEFAULT_VALIDATION_POSTURE = "not-validated-outside-document"
DEFAULT_EVIDENCE_ROLE = "document-local-evidence"
MANAGED_COPY_POLICY = "raw-source-files-not-copied-by-default"
_COMPACT_PREVIEW_LIMIT = 240
_SLUG_RE = re.compile(r"[^a-z0-9]+")

Clock = Callable[[], datetime]
IdFactory = Callable[[str], str]


@dataclass(frozen=True)
class ManifestMetadata:
    """Shared schema/version/privacy metadata embedded in every manifest."""

    schema_version: str
    created_at: str
    updated_at: str
    generator: str = PROJECT_SOURCE_GENERATOR
    local_private_boundary: str = LOCAL_PRIVATE_BOUNDARY_MARKER
    managed_copy_policy: str = MANAGED_COPY_POLICY


@dataclass(frozen=True)
class Project:
    """Minimal durable local Project manifest."""

    project_id: str
    name: str
    description: str | None
    created_at: str
    updated_at: str
    schema_version: str = PROJECT_SOURCE_SCHEMA_VERSION
    privacy_class: str = DEFAULT_PRIVACY_CLASS
    project_source_ids: tuple[str, ...] = ()
    retention_state: str = DEFAULT_RETENTION_STATE
    manifest_metadata: ManifestMetadata | None = None


@dataclass(frozen=True)
class SourceRecord:
    """Compact source inventory record for a document-review-derived source."""

    source_record_id: str
    source_kind: str
    privacy_class: str
    title: str
    document_id: str
    document_hash: str
    byte_hash: str | None
    created_at: str
    updated_at: str
    schema_version: str = PROJECT_SOURCE_SCHEMA_VERSION
    retention_state: str = DEFAULT_RETENTION_STATE
    manifest_metadata: ManifestMetadata | None = None


@dataclass(frozen=True)
class SourceRevision:
    """Compact source revision manifest without raw document content."""

    source_revision_id: str
    source_record_id: str
    document_id: str
    document_hash: str
    byte_hash: str | None
    parser_metadata: dict[str, object]
    anchor_manifest: tuple[dict[str, object], ...]
    chunk_manifest: tuple[dict[str, object], ...]
    finding_manifest: tuple[dict[str, object], ...]
    source_obligation_summary: dict[str, object]
    boundary_notice: str
    privacy_warning: str
    created_at: str
    updated_at: str
    schema_version: str = PROJECT_SOURCE_SCHEMA_VERSION
    privacy_class: str = DEFAULT_PRIVACY_CLASS
    retention_state: str = DEFAULT_RETENTION_STATE
    local_private_boundary: str = LOCAL_PRIVATE_BOUNDARY_MARKER
    raw_text_persisted: bool = False
    manifest_metadata: ManifestMetadata | None = None


@dataclass(frozen=True)
class ProjectSource:
    """Project membership edge for one saved source revision."""

    project_source_id: str
    project_id: str
    source_record_id: str
    source_revision_id: str
    title: str
    source_kind: str
    scope: str
    privacy_class: str
    evidence_role: str
    source_obligation_summary: dict[str, object]
    validation_posture: str
    source_identity: dict[str, object]
    parser_metadata: dict[str, object]
    anchor_manifest_ref: str
    chunk_manifest_ref: str
    retention_state: str
    added_at: str
    updated_at: str
    schema_version: str = PROJECT_SOURCE_SCHEMA_VERSION
    local_private_boundary: str = LOCAL_PRIVATE_BOUNDARY_MARKER
    raw_text_persisted: bool = False
    manifest_metadata: ManifestMetadata | None = None


@dataclass(frozen=True)
class ProjectSourcePromotionResult:
    """Return packet for a document-review ProjectSource promotion."""

    project: Project
    project_source: ProjectSource
    source_record: SourceRecord
    source_revision: SourceRevision
    project_manifest_path: Path
    project_source_manifest_path: Path
    source_record_manifest_path: Path
    source_revision_manifest_path: Path


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def default_id_factory(prefix: str) -> str:
    """Return a stable-format locally unique ID."""

    return f"{prefix}_{uuid4().hex}"


def default_storage_root() -> Path:
    """Return the default local ignored storage root for project/source manifests."""

    return DEFAULT_PROJECT_SOURCE_STORAGE_ROOT


def create_project(
    name: str,
    *,
    description: str | None = None,
    storage_root: str | Path | None = None,
    clock: Clock = utc_now,
    id_factory: IdFactory = default_id_factory,
) -> Project:
    """Create and persist a minimal local Project manifest."""

    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name is required.")
    root = _prepare_storage_root(storage_root)
    timestamp = _timestamp(clock)
    project = Project(
        project_id=id_factory("proj"),
        name=clean_name,
        description=description.strip() if description and description.strip() else None,
        created_at=timestamp,
        updated_at=timestamp,
        manifest_metadata=_manifest_metadata(timestamp, timestamp),
    )
    _write_json(_project_path(root, project.project_id), _project_payload(project))
    return project


def list_projects(*, storage_root: str | Path | None = None) -> tuple[Project, ...]:
    """List active/non-active Project manifests under the local storage root."""

    root = _prepare_storage_root(storage_root, create=False)
    projects_dir = root / "projects"
    if not projects_dir.exists():
        return ()
    return tuple(
        sorted(
            (_project_from_payload(_read_json(path)) for path in projects_dir.glob("*.json")),
            key=lambda p: p.created_at,
        )
    )


def load_project(project_id: str, *, storage_root: str | Path | None = None) -> Project:
    """Load one Project manifest by ID."""

    root = _prepare_storage_root(storage_root, create=False)
    return _project_from_payload(_read_json(_project_path(root, project_id)))


def update_project(
    project: Project,
    *,
    storage_root: str | Path | None = None,
    clock: Clock = utc_now,
) -> Project:
    """Persist an updated Project manifest with a fresh updated_at timestamp."""

    root = _prepare_storage_root(storage_root)
    updated_at = _timestamp(clock)
    updated = Project(
        project_id=project.project_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=updated_at,
        schema_version=project.schema_version,
        privacy_class=project.privacy_class,
        project_source_ids=tuple(project.project_source_ids),
        retention_state=project.retention_state,
        manifest_metadata=_manifest_metadata(project.created_at, updated_at),
    )
    _write_json(_project_path(root, updated.project_id), _project_payload(updated))
    return updated


def add_project_source_from_document_review(
    project: Project | str,
    context: DocumentReviewContext,
    *,
    storage_root: str | Path | None = None,
    title: str | None = None,
    clock: Clock = utc_now,
    id_factory: IdFactory = default_id_factory,
) -> ProjectSourcePromotionResult:
    """Promote a DocumentReviewContext into compact local Project Source manifests.

    The promotion preserves document identity, parser metadata, anchor/chunk IDs,
    bounded previews, finding classifications, source-obligation summaries, and
    explicit local/private boundary markers. It deliberately omits
    ``context.normalized_text``, chunk full text, anchor full text, and finding full
    text so raw private document text is not persisted by default.
    """

    root = _prepare_storage_root(storage_root)
    loaded_project = load_project(project, storage_root=root) if isinstance(project, str) else project
    timestamp = _timestamp(clock)
    source_title = (title or context.metadata.title).strip() or context.metadata.document_id
    source_kind = f"document-review-{context.metadata.input_format}"
    source_record_id = id_factory("src")
    source_revision_id = id_factory("rev")
    project_source_id = id_factory("psrc")
    parser_metadata = _parser_metadata(context)
    anchor_manifest = _anchor_manifest(context)
    chunk_manifest = _chunk_manifest(context)
    finding_manifest = _finding_manifest(context)
    obligation_summary = _source_obligation_summary(context)
    byte_hash = _byte_hash_from_document_hash(context.metadata.document_hash)
    source_record = SourceRecord(
        source_record_id=source_record_id,
        source_kind=source_kind,
        privacy_class=DEFAULT_PRIVACY_CLASS,
        title=source_title,
        document_id=context.metadata.document_id,
        document_hash=context.metadata.document_hash,
        byte_hash=byte_hash,
        created_at=timestamp,
        updated_at=timestamp,
        manifest_metadata=_manifest_metadata(timestamp, timestamp),
    )
    source_revision = SourceRevision(
        source_revision_id=source_revision_id,
        source_record_id=source_record_id,
        document_id=context.metadata.document_id,
        document_hash=context.metadata.document_hash,
        byte_hash=byte_hash,
        parser_metadata=parser_metadata,
        anchor_manifest=anchor_manifest,
        chunk_manifest=chunk_manifest,
        finding_manifest=finding_manifest,
        source_obligation_summary=obligation_summary,
        boundary_notice=context.boundary_notice or BOUNDARY_NOTICE,
        privacy_warning=context.privacy_warning or PRIVACY_WARNING,
        created_at=timestamp,
        updated_at=timestamp,
        manifest_metadata=_manifest_metadata(timestamp, timestamp),
    )
    project_source = ProjectSource(
        project_source_id=project_source_id,
        project_id=loaded_project.project_id,
        source_record_id=source_record_id,
        source_revision_id=source_revision_id,
        title=source_title,
        source_kind=source_kind,
        scope=PROJECT_SCOPE,
        privacy_class=DEFAULT_PRIVACY_CLASS,
        evidence_role=DEFAULT_EVIDENCE_ROLE,
        source_obligation_summary=obligation_summary,
        validation_posture=DEFAULT_VALIDATION_POSTURE,
        source_identity={
            "document_id": context.metadata.document_id,
            "document_hash": context.metadata.document_hash,
            "byte_hash": byte_hash,
            "input_format": context.metadata.input_format,
            "document_review_version": context.metadata.version,
            "document_privacy_marker": context.metadata.privacy_marker,
        },
        parser_metadata=parser_metadata,
        anchor_manifest_ref=f"source_revisions/{source_revision_id}.json#anchor_manifest",
        chunk_manifest_ref=f"source_revisions/{source_revision_id}.json#chunk_manifest",
        retention_state=DEFAULT_RETENTION_STATE,
        added_at=timestamp,
        updated_at=timestamp,
        manifest_metadata=_manifest_metadata(timestamp, timestamp),
    )
    project_ids = tuple(dict.fromkeys((*loaded_project.project_source_ids, project_source_id)))
    updated_project = Project(
        project_id=loaded_project.project_id,
        name=loaded_project.name,
        description=loaded_project.description,
        created_at=loaded_project.created_at,
        updated_at=timestamp,
        schema_version=loaded_project.schema_version,
        privacy_class=loaded_project.privacy_class,
        project_source_ids=project_ids,
        retention_state=loaded_project.retention_state,
        manifest_metadata=_manifest_metadata(loaded_project.created_at, timestamp),
    )
    project_path = _project_path(root, updated_project.project_id)
    project_source_path = _project_source_path(root, project_source_id)
    source_record_path = _source_record_path(root, source_record_id)
    source_revision_path = _source_revision_path(root, source_revision_id)
    _write_json(source_record_path, _source_record_payload(source_record))
    _write_json(source_revision_path, _source_revision_payload(source_revision))
    _write_json(project_source_path, _project_source_payload(project_source))
    _write_json(project_path, _project_payload(updated_project))
    return ProjectSourcePromotionResult(
        project=updated_project,
        project_source=project_source,
        source_record=source_record,
        source_revision=source_revision,
        project_manifest_path=project_path,
        project_source_manifest_path=project_source_path,
        source_record_manifest_path=source_record_path,
        source_revision_manifest_path=source_revision_path,
    )


def list_project_sources(
    project: Project | str, *, storage_root: str | Path | None = None
) -> tuple[ProjectSource, ...]:
    """List ProjectSource manifests linked from a Project manifest."""

    root = _prepare_storage_root(storage_root, create=False)
    loaded_project = load_project(project, storage_root=root) if isinstance(project, str) else project
    sources: list[ProjectSource] = []
    for project_source_id in loaded_project.project_source_ids:
        path = _project_source_path(root, project_source_id)
        if path.exists():
            sources.append(_project_source_from_payload(_read_json(path)))
    return tuple(sources)


def load_project_source(project_source_id: str, *, storage_root: str | Path | None = None) -> ProjectSource:
    """Load one ProjectSource manifest by ID."""

    root = _prepare_storage_root(storage_root, create=False)
    return _project_source_from_payload(_read_json(_project_source_path(root, project_source_id)))


def load_source_record(source_record_id: str, *, storage_root: str | Path | None = None) -> SourceRecord:
    """Load one SourceRecord manifest by ID."""

    root = _prepare_storage_root(storage_root, create=False)
    return _source_record_from_payload(_read_json(_source_record_path(root, source_record_id)))


def load_source_revision(source_revision_id: str, *, storage_root: str | Path | None = None) -> SourceRevision:
    """Load one SourceRevision manifest by ID."""

    root = _prepare_storage_root(storage_root, create=False)
    return _source_revision_from_payload(_read_json(_source_revision_path(root, source_revision_id)))


def remove_project_source(
    project: Project | str,
    project_source_id: str,
    *,
    storage_root: str | Path | None = None,
    clock: Clock = utc_now,
) -> Project:
    """Mark a ProjectSource membership edge removed without deleting source manifests."""

    root = _prepare_storage_root(storage_root)
    loaded_project = load_project(project, storage_root=root) if isinstance(project, str) else project
    updated_at = _timestamp(clock)
    project_source_path = _project_source_path(root, project_source_id)
    if project_source_path.exists():
        project_source = _project_source_from_payload(_read_json(project_source_path))
        removed_project_source = ProjectSource(
            project_source_id=project_source.project_source_id,
            project_id=project_source.project_id,
            source_record_id=project_source.source_record_id,
            source_revision_id=project_source.source_revision_id,
            title=project_source.title,
            source_kind=project_source.source_kind,
            scope=project_source.scope,
            privacy_class=project_source.privacy_class,
            evidence_role=project_source.evidence_role,
            source_obligation_summary=project_source.source_obligation_summary,
            validation_posture=project_source.validation_posture,
            source_identity=project_source.source_identity,
            parser_metadata=project_source.parser_metadata,
            anchor_manifest_ref=project_source.anchor_manifest_ref,
            chunk_manifest_ref=project_source.chunk_manifest_ref,
            retention_state="removed-from-project",
            added_at=project_source.added_at,
            updated_at=updated_at,
            schema_version=project_source.schema_version,
            local_private_boundary=project_source.local_private_boundary,
            raw_text_persisted=project_source.raw_text_persisted,
            manifest_metadata=_manifest_metadata(project_source.added_at, updated_at),
        )
        _write_json(project_source_path, _project_source_payload(removed_project_source))
    updated = Project(
        project_id=loaded_project.project_id,
        name=loaded_project.name,
        description=loaded_project.description,
        created_at=loaded_project.created_at,
        updated_at=updated_at,
        schema_version=loaded_project.schema_version,
        privacy_class=loaded_project.privacy_class,
        project_source_ids=tuple(psid for psid in loaded_project.project_source_ids if psid != project_source_id),
        retention_state=loaded_project.retention_state,
        manifest_metadata=_manifest_metadata(loaded_project.created_at, updated_at),
    )
    _write_json(_project_path(root, updated.project_id), _project_payload(updated))
    return updated


def _prepare_storage_root(storage_root: str | Path | None, *, create: bool = True) -> Path:
    root = Path(storage_root) if storage_root is not None else default_storage_root()
    if create:
        for child in ("projects", "project_sources", "source_records", "source_revisions"):
            (root / child).mkdir(parents=True, exist_ok=True)
    return root


def _timestamp(clock: Clock) -> str:
    return clock().astimezone(timezone.utc).isoformat()


def _manifest_metadata(created_at: str, updated_at: str) -> ManifestMetadata:
    return ManifestMetadata(
        schema_version=PROJECT_SOURCE_SCHEMA_VERSION,
        created_at=created_at,
        updated_at=updated_at,
    )


def _project_path(root: Path, project_id: str) -> Path:
    return root / "projects" / f"{_safe_id(project_id)}.json"


def _project_source_path(root: Path, project_source_id: str) -> Path:
    return root / "project_sources" / f"{_safe_id(project_source_id)}.json"


def _source_record_path(root: Path, source_record_id: str) -> Path:
    return root / "source_records" / f"{_safe_id(source_record_id)}.json"


def _source_revision_path(root: Path, source_revision_id: str) -> Path:
    return root / "source_revisions" / f"{_safe_id(source_revision_id)}.json"


def _safe_id(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier):
        raise ValueError(f"Unsafe manifest identifier: {identifier!r}")
    return identifier


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest is not a JSON object: {path}")
    return payload


def _project_payload(project: Project) -> dict[str, object]:
    payload = asdict(project)
    payload["project_source_ids"] = list(project.project_source_ids)
    return payload


def _source_record_payload(source_record: SourceRecord) -> dict[str, object]:
    return asdict(source_record)


def _source_revision_payload(source_revision: SourceRevision) -> dict[str, object]:
    payload = asdict(source_revision)
    payload["anchor_manifest"] = list(source_revision.anchor_manifest)
    payload["chunk_manifest"] = list(source_revision.chunk_manifest)
    payload["finding_manifest"] = list(source_revision.finding_manifest)
    return payload


def _project_source_payload(project_source: ProjectSource) -> dict[str, object]:
    return asdict(project_source)


def _project_from_payload(payload: dict[str, object]) -> Project:
    return Project(
        project_id=str(payload["project_id"]),
        name=str(payload["name"]),
        description=payload.get("description") if isinstance(payload.get("description"), str) else None,
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        schema_version=str(payload.get("schema_version", PROJECT_SOURCE_SCHEMA_VERSION)),
        privacy_class=str(payload.get("privacy_class", DEFAULT_PRIVACY_CLASS)),
        project_source_ids=tuple(str(item) for item in payload.get("project_source_ids", [])),
        retention_state=str(payload.get("retention_state", DEFAULT_RETENTION_STATE)),
        manifest_metadata=_manifest_from_payload(payload.get("manifest_metadata")),
    )


def _source_record_from_payload(payload: dict[str, object]) -> SourceRecord:
    return SourceRecord(
        source_record_id=str(payload["source_record_id"]),
        source_kind=str(payload["source_kind"]),
        privacy_class=str(payload.get("privacy_class", DEFAULT_PRIVACY_CLASS)),
        title=str(payload["title"]),
        document_id=str(payload["document_id"]),
        document_hash=str(payload["document_hash"]),
        byte_hash=payload.get("byte_hash") if isinstance(payload.get("byte_hash"), str) else None,
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        schema_version=str(payload.get("schema_version", PROJECT_SOURCE_SCHEMA_VERSION)),
        retention_state=str(payload.get("retention_state", DEFAULT_RETENTION_STATE)),
        manifest_metadata=_manifest_from_payload(payload.get("manifest_metadata")),
    )


def _source_revision_from_payload(payload: dict[str, object]) -> SourceRevision:
    return SourceRevision(
        source_revision_id=str(payload["source_revision_id"]),
        source_record_id=str(payload["source_record_id"]),
        document_id=str(payload["document_id"]),
        document_hash=str(payload["document_hash"]),
        byte_hash=payload.get("byte_hash") if isinstance(payload.get("byte_hash"), str) else None,
        parser_metadata=dict(payload.get("parser_metadata", {})),
        anchor_manifest=tuple(_dict_items(payload.get("anchor_manifest", []))),
        chunk_manifest=tuple(_dict_items(payload.get("chunk_manifest", []))),
        finding_manifest=tuple(_dict_items(payload.get("finding_manifest", []))),
        source_obligation_summary=dict(payload.get("source_obligation_summary", {})),
        boundary_notice=str(payload.get("boundary_notice", BOUNDARY_NOTICE)),
        privacy_warning=str(payload.get("privacy_warning", PRIVACY_WARNING)),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        schema_version=str(payload.get("schema_version", PROJECT_SOURCE_SCHEMA_VERSION)),
        privacy_class=str(payload.get("privacy_class", DEFAULT_PRIVACY_CLASS)),
        retention_state=str(payload.get("retention_state", DEFAULT_RETENTION_STATE)),
        local_private_boundary=str(payload.get("local_private_boundary", LOCAL_PRIVATE_BOUNDARY_MARKER)),
        raw_text_persisted=bool(payload.get("raw_text_persisted", False)),
        manifest_metadata=_manifest_from_payload(payload.get("manifest_metadata")),
    )


def _project_source_from_payload(payload: dict[str, object]) -> ProjectSource:
    return ProjectSource(
        project_source_id=str(payload["project_source_id"]),
        project_id=str(payload["project_id"]),
        source_record_id=str(payload["source_record_id"]),
        source_revision_id=str(payload["source_revision_id"]),
        title=str(payload["title"]),
        source_kind=str(payload["source_kind"]),
        scope=str(payload.get("scope", PROJECT_SCOPE)),
        privacy_class=str(payload.get("privacy_class", DEFAULT_PRIVACY_CLASS)),
        evidence_role=str(payload.get("evidence_role", DEFAULT_EVIDENCE_ROLE)),
        source_obligation_summary=dict(payload.get("source_obligation_summary", {})),
        validation_posture=str(payload.get("validation_posture", DEFAULT_VALIDATION_POSTURE)),
        source_identity=dict(payload.get("source_identity", {})),
        parser_metadata=dict(payload.get("parser_metadata", {})),
        anchor_manifest_ref=str(payload.get("anchor_manifest_ref", "")),
        chunk_manifest_ref=str(payload.get("chunk_manifest_ref", "")),
        retention_state=str(payload.get("retention_state", DEFAULT_RETENTION_STATE)),
        added_at=str(payload["added_at"]),
        updated_at=str(payload["updated_at"]),
        schema_version=str(payload.get("schema_version", PROJECT_SOURCE_SCHEMA_VERSION)),
        local_private_boundary=str(payload.get("local_private_boundary", LOCAL_PRIVATE_BOUNDARY_MARKER)),
        raw_text_persisted=bool(payload.get("raw_text_persisted", False)),
        manifest_metadata=_manifest_from_payload(payload.get("manifest_metadata")),
    )


def _manifest_from_payload(payload: object) -> ManifestMetadata | None:
    if not isinstance(payload, dict):
        return None
    return ManifestMetadata(
        schema_version=str(payload.get("schema_version", PROJECT_SOURCE_SCHEMA_VERSION)),
        created_at=str(payload.get("created_at", "")),
        updated_at=str(payload.get("updated_at", "")),
        generator=str(payload.get("generator", PROJECT_SOURCE_GENERATOR)),
        local_private_boundary=str(payload.get("local_private_boundary", LOCAL_PRIVATE_BOUNDARY_MARKER)),
        managed_copy_policy=str(payload.get("managed_copy_policy", MANAGED_COPY_POLICY)),
    )


def _dict_items(items: object) -> Iterable[dict[str, object]]:
    if not isinstance(items, list):
        return ()
    return tuple(dict(item) for item in items if isinstance(item, dict))


def _parser_metadata(context: DocumentReviewContext) -> dict[str, object]:
    metadata = context.metadata
    return {
        "input_format": metadata.input_format,
        "parser_name": metadata.parser_name,
        "parser_version": metadata.parser_version,
        "parser_confidence": metadata.parser_confidence,
        "parser_notes": list(metadata.parser_notes),
        "document_review_version": metadata.version,
        "context_parser_metadata": _jsonable(context.parser_metadata),
    }


def _anchor_manifest(context: DocumentReviewContext) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "anchor_id": anchor.anchor_id,
            "section_id": anchor.section_id,
            "section_heading": anchor.section_heading,
            "kind": anchor.kind,
            "start_line": anchor.start_line,
            "end_line": anchor.end_line,
            "line_reference": anchor.line_reference,
            "source_reference": anchor.source_reference,
            "extraction_confidence": anchor.extraction_confidence,
            "source_format": anchor.source_format,
            "parser_name": anchor.parser_name,
            "parser_version": anchor.parser_version,
            "source_page_start": anchor.source_page_start,
            "source_page_end": anchor.source_page_end,
            "source_block_start": anchor.source_block_start,
            "source_block_end": anchor.source_block_end,
            "anchor_note": anchor.anchor_note,
            "text_preview": _bounded_preview(anchor.text),
        }
        for anchor in context.anchors
    )


def _chunk_manifest(context: DocumentReviewContext) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "document_hash": chunk.document_hash,
            "section_id": chunk.section_id,
            "section_heading": chunk.section_heading,
            "anchor_ids": list(chunk.anchor_ids),
            "preview": _bounded_preview(chunk.preview),
            "extraction_confidence": chunk.extraction_confidence,
            "evidence_label": chunk.evidence_label,
            "locality_label": chunk.locality_label,
            "source_scope": chunk.source_scope,
            "retrieval_mode": chunk.retrieval_mode,
        }
        for chunk in context.chunks
    )


def _finding_manifest(context: DocumentReviewContext) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "finding_id": finding.finding_id,
            "labels": list(finding.labels),
            "anchor_ids": list(finding.anchor_ids),
            "extraction_confidence": finding.extraction_confidence,
            "note_preview": _bounded_preview(finding.note),
            "claim_type": finding.claim_type,
            "source_obligation": finding.source_obligation,
            "evidence_role": finding.evidence_role,
            "validation_need": finding.validation_need,
            "risk_level": finding.risk_level,
        }
        for finding in context.findings
    )


def _source_obligation_summary(context: DocumentReviewContext) -> dict[str, object]:
    obligation_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}
    claim_type_counts: dict[str, int] = {}
    evidence_role_counts: dict[str, int] = {}
    validation_need_counts: dict[str, int] = {}
    risk_level_counts: dict[str, int] = {}
    for finding in context.findings:
        _count(obligation_counts, finding.source_obligation)
        _count(claim_type_counts, finding.claim_type)
        _count(evidence_role_counts, finding.evidence_role)
        _count(validation_need_counts, finding.validation_need)
        _count(risk_level_counts, finding.risk_level)
        for label in finding.labels:
            _count(label_counts, label)
    return {
        "finding_count": len(context.findings),
        "obligation_counts": obligation_counts,
        "label_counts": label_counts,
        "claim_type_counts": claim_type_counts,
        "evidence_role_counts": evidence_role_counts,
        "validation_need_counts": validation_need_counts,
        "risk_level_counts": risk_level_counts,
        "source_scope": DOCUMENT_SOURCE_SCOPE,
        "evidence_label": DOCUMENT_LOCAL_EVIDENCE_LABEL,
        "validation_posture": DEFAULT_VALIDATION_POSTURE,
    }


def _count(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _bounded_preview(text: str, *, limit: int = _COMPACT_PREVIEW_LIMIT) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    return value


def _byte_hash_from_document_hash(document_hash: str) -> str | None:
    # DocumentReviewContext exposes a normalized extracted-text hash, not source
    # bytes. AG-84B records None rather than inventing a raw byte hash.
    return None


def project_slug(name: str) -> str:
    """Return a human-readable slug helper for UI/future path display only."""

    slug = _SLUG_RE.sub("-", name.lower()).strip("-")
    return slug or "project"
