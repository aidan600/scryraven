"""Local session custody, serialization and transactions; no semantic decisions."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from scryraven.documents import (
    DOCUMENT_ID,
    PreparedDocument,
    SessionDocument,
    document_text_view,
    prepare_pdf,
)
from scryraven.errors import RunError
from scryraven.historical import Analysis, validate_historical_analysis
from scryraven.images import MAX_ATTACHMENT_REQUEST_BYTES, MAX_ATTACHMENTS_PER_QUESTION, PreparedImage, SessionImage
from scryraven.model import valid_model_identifier
from scryraven.presentation import Citation, CitationUse
from scryraven.run_settings import BILLED_BACKENDS, RunSettings
from scryraven.sources import Evidence, SupportRegion, exact_view, support_text


@dataclass(frozen=True)
class SessionTurn:
    """Completed public answer and its exact presentation snapshot, without traces."""

    question: str
    answer: str
    # Legacy semantic history only. Source-first completed answers do not invent
    # an Analyst result merely to use the same custody and presentation boundary.
    analysis: Analysis | None
    posture: str
    stop_reason: str
    selected_evidence: tuple[Evidence, ...] = ()
    citations: tuple[Citation, ...] = ()
    citation_uses: tuple[CitationUse, ...] = ()
    image_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionState:
    turns: tuple[SessionTurn, ...] = ()
    acquisitions: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class SessionMetadata:
    session_id: str
    created_at: str
    updated_at: str
    title: str
    revision: int
    citation_language: str = "en"


@dataclass(frozen=True)
class StoredSession:
    metadata: SessionMetadata
    state: SessionState
    documents: tuple[SessionDocument, ...] = ()
    images: tuple[SessionImage, ...] = ()


@dataclass(frozen=True)
class AttachedDocument:
    document: SessionDocument
    created: bool


class SessionStoreError(RuntimeError):
    """Fixed public code; never includes database paths, contents or OS messages."""

    def __init__(self, code: str = "session_store_unavailable") -> None:
        super().__init__(code)
        self.code = code


class SessionConflictError(SessionStoreError):
    def __init__(self) -> None:
        super().__init__("session_conflict")


class SessionStore(Protocol):
    """Application boundary shared by any shell; one completed turn per commit."""

    def create(self, title: str = "") -> StoredSession: ...
    def load(self, session_id: str) -> StoredSession: ...
    def list_sessions(self) -> tuple[SessionMetadata, ...]: ...
    def commit(self, session_id: str, revision: int, state: SessionState) -> SessionMetadata: ...
    def rename(self, session_id: str, title: str) -> SessionMetadata: ...
    def delete(self, session_id: str, *, revision: int | None = None) -> None: ...
    def attach_document(self, session_id: str, revision: int, filename: str,
                        media_type: str, data: bytes) -> AttachedDocument: ...


def default_session_path() -> Path:
    """Per-user application data, independent of the checkout and current directory."""
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        if not root.is_absolute():
            root = Path.home() / "AppData" / "Local"
        return root / "ScryRaven" / "sessions.sqlite3"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ScryRaven" / "sessions.sqlite3"
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    if not root.is_absolute():
        root = Path.home() / ".local" / "share"
    return root / "scryraven" / "sessions.sqlite3"


# The wire types intentionally whitelist product state. Result.trace, transport
# state, corrections, cache keys and raw model responses have no storage field.
class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _EvidenceRecord(_Record):
    id: str
    url: str
    title: str
    content: str
    acquisition: Literal["provider_highlights", "fetched_source", "targeted_view"]
    source_id: str
    parent_id: str | None
    start_char: int | None
    end_char: int | None
    source_kind: Literal["web", "user_document"] = "web"
    document_id: str | None = None
    filename: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    visual_analysis: bool | None = None
    textless_page_count: int | None = None
    range_basis: Literal["acquired_highlight"] | None = None


class _CitationRecord(_Record):
    number: int
    source_id: str
    title: str
    url: str
    material_ids: list[str]
    source_kind: Literal["web", "user_document"] = "web"
    document_id: str | None = None
    filename: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    description: str | None = None


class _SupportRecord(_Record):
    evidence_ref: str
    start_char: int
    end_char: int
    material_sha256: str
    passage_sha256: str


class _UseRecord(_Record):
    number: int
    start: int
    end: int
    support: list[_SupportRecord] = Field(default_factory=list)


class _TurnRecord(_Record):
    question: str
    answer: str
    analysis: Analysis | None
    posture: Literal["supported", "partial", "unable"]
    stop_reason: Literal["supported", "not_established", "research_bound", "navigation_bound"]
    selected_evidence: list[_EvidenceRecord]
    citations: list[_CitationRecord]
    citation_uses: list[_UseRecord]
    image_ids: list[str] = Field(default_factory=list)


class _StateRecord(_Record):
    turns: list[_TurnRecord]
    acquisitions: list[_EvidenceRecord]


class _MetadataRecord(_Record):
    session_id: str
    created_at: str
    updated_at: str
    title: str
    revision: int
    citation_language: str = "en"


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid_session_data")


def _metadata(row: sqlite3.Row) -> SessionMetadata:
    record = _MetadataRecord.model_validate({name: row[name] for name in _MetadataRecord.model_fields})
    _require(len(record.session_id) == 32 and all(c in "0123456789abcdef" for c in record.session_id))
    created, updated = datetime.fromisoformat(record.created_at), datetime.fromisoformat(record.updated_at)
    _require(created.tzinfo is not None and updated.tzinfo is not None and updated >= created)
    _require(record.revision >= 0)
    _require(record.citation_language in CITATION_LANGUAGES)
    return SessionMetadata(**record.model_dump())


def _evidence(record: _EvidenceRecord) -> Evidence:
    if record.source_kind == "user_document":
        _require(bool(record.id and record.source_id and record.content and not record.url.strip()))
    else:
        _require(bool(record.id and record.source_id and record.url.strip() and record.content.strip()))
    return Evidence(**record.model_dump())


def _decode(payload: str, revision: int, documents: tuple[SessionDocument, ...] = (),
            images: tuple[SessionImage, ...] = ()) -> SessionState:
    record = _StateRecord.model_validate_json(payload)
    _require(len(record.turns) == revision)
    acquisitions = tuple(_evidence(item) for item in record.acquisitions)
    _require(all(item.source_kind == "web" for item in acquisitions))
    by_id = {item.id: item for item in acquisitions}
    by_document = {item.document_id: item for item in documents}
    by_url: dict[str, str] = {}
    for index, item in enumerate(acquisitions, 1):
        # The existing allocator uses corpus length. Validate its invariant, never
        # repair or renumber IDs on load, including same-URL acquisition versions.
        _require(item.id == f"E{index}" and item.acquisition != "targeted_view")
        _require(item.source_id == by_url.setdefault(item.url, item.id))
    _require(bool(record.turns) or not acquisitions)
    turns = []
    for saved in record.turns:
        _require(len(set(saved.image_ids)) == len(saved.image_ids)
                 and set(saved.image_ids) <= {image.image_id for image in images})
        _require(bool(saved.question.strip() and saved.answer.strip()))
        selected = tuple(_evidence(item) for item in saved.selected_evidence)
        materials = {item.id: item for item in selected}
        _require(len(materials) == len(selected))
        for item in selected:
            if item.source_kind == "user_document":
                _require(item == document_text_view(by_document[item.document_id], item.start_char, item.end_char))
            elif item.acquisition == "targeted_view":
                parent = by_id[item.parent_id]
                _require(item == exact_view(parent, item.start_char, item.end_char))
            else:
                _require(by_id[item.id] == item)
        analysis = saved.analysis
        if analysis is not None:
            original = analysis.model_dump()
            validate_historical_analysis(analysis, list(acquisitions), [])
            _require(analysis.model_dump() == original)  # Reconstruction never corrects history.
            _require(set(analysis.support_refs) == {item.source_id for item in selected})
            posture = "supported" if analysis.decision == "supported" else ("partial" if analysis.findings else "unable")
            _require(saved.posture == posture)
            if analysis.decision == "supported":
                _require(saved.stop_reason == "supported")
            elif analysis.decision == "research_needed":
                _require(saved.stop_reason == "research_bound")
            else:
                _require(saved.stop_reason in {"not_established", "navigation_bound"})
        citations = tuple(Citation(
            c.number, c.source_id, c.title, c.url, tuple(materials[ref] for ref in c.material_ids),
            c.source_kind, c.document_id, c.filename, c.page_start, c.page_end,
            description=c.description,
        ) for c in saved.citations)
        _require(len({c.source_id for c in citations}) == len(citations))
        for number, citation in enumerate(citations, 1):
            _require(citation.number == number)
            _require(bool(citation.materials) and citation.materials == tuple(
                item for item in selected if item.source_id == citation.source_id))
            if citation.source_kind == "user_document":
                document = by_document[citation.document_id]
                pages = [item.page_start for item in citation.materials]
                page_ends = [item.page_end for item in citation.materials]
                _require(citation.source_id == document.document_id == citation.document_id)
                _require(citation.url == "" and citation.title == citation.filename == document.filename)
                _require(citation.page_start == min(pages) and citation.page_end == max(page_ends))
            else:
                source = by_id[citation.source_id]
                _require(citation.source_kind == "web" and citation.document_id is None)
                _require(citation.filename is None and citation.page_start is None and citation.page_end is None)
                _require(source.id == source.source_id)
                _require((citation.title, citation.url) == (source.title, source.url))
        uses = tuple(CitationUse(item.number, item.start, item.end,
                                tuple(SupportRegion(**region.model_dump()) for region in item.support))
                     for item in saved.citation_uses)
        end = 0
        for use in uses:
            _require(1 <= use.number <= len(citations) and end <= use.start < use.end <= len(saved.answer))
            _require(saved.answer[use.start:use.end] == f"[{use.number}]")
            source_materials = {item.id: item for item in citations[use.number - 1].materials}
            _require(len(use.support) == len(set(use.support)))
            for region in use.support:
                support_text(region, source_materials[region.evidence_ref])
            end = use.end
        _require(list(dict.fromkeys(use.number for use in uses)) == list(range(1, len(citations) + 1)))
        _require(not any(use.support for use in uses) or all(use.support for use in uses))
        if analysis is not None or saved.posture != "unable":
            # Native source-free premise derivations have neither selected
            # material nor citations. Answer validates their semantic basis.
            _require(bool(citations) == bool(selected))
        turns.append(SessionTurn(saved.question, saved.answer, analysis, saved.posture, saved.stop_reason,
                                 selected, citations, uses, tuple(saved.image_ids)))
    return SessionState(tuple(turns), acquisitions)


def _citation_record(citation: Citation) -> dict:
    row = {"number": citation.number, "source_id": citation.source_id, "title": citation.title,
           "url": citation.url, "material_ids": [item.id for item in citation.materials]}
    if citation.source_kind != "web":
        row.update(source_kind=citation.source_kind, document_id=citation.document_id,
                   filename=citation.filename, page_start=citation.page_start, page_end=citation.page_end)
    if citation.description is not None:
        row["description"] = citation.description
    return row


def _encode(state: SessionState, documents: tuple[SessionDocument, ...] = (),
            images: tuple[SessionImage, ...] = ()) -> str:
    # Citation material references resolve only against this turn's saved packet.
    # Web evidence keeps the schema-1 key set. Document bytes stay out of this payload.
    turns = []
    for turn in state.turns:
        turns.append({
            "question": turn.question, "answer": turn.answer,
            "analysis": turn.analysis.model_dump() if turn.analysis is not None else None,
            "posture": turn.posture, "stop_reason": turn.stop_reason,
            "selected_evidence": [item.material() for item in turn.selected_evidence],
            "citations": [_citation_record(c) for c in turn.citations],
            "citation_uses": [{"number": use.number, "start": use.start, "end": use.end,
                               **({"support": [asdict(region) for region in use.support]} if use.support else {})}
                              for use in turn.citation_uses],
            **({"image_ids": list(turn.image_ids)} if turn.image_ids else {}),
        })
    payload = json.dumps({"turns": turns, "acquisitions": [item.material() for item in state.acquisitions]},
                         ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    _require(_decode(payload, len(state.turns), documents, images) == state)
    return payload


_SESSIONS_SQL = """CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    title TEXT NOT NULL, revision INTEGER NOT NULL CHECK (revision >= 0), payload TEXT NOT NULL,
    citation_language TEXT NOT NULL DEFAULT 'en'
)"""

CITATION_LANGUAGES = ("en", "match", "es", "fr", "de", "pl", "ja", "zh", "ar", "pt")

_IMAGES_SQL = """CREATE TABLE IF NOT EXISTS session_images (
    session_id TEXT NOT NULL, image_id TEXT NOT NULL, filename TEXT NOT NULL,
    media_type TEXT NOT NULL, byte_length INTEGER NOT NULL, sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, original_image BLOB NOT NULL,
    PRIMARY KEY (session_id, image_id), UNIQUE (session_id, sha256)
)"""

_JOBS_SQL = """CREATE TABLE IF NOT EXISTS research_jobs (
    job_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
    fingerprint TEXT NOT NULL, question TEXT NOT NULL, revision INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('queued','researching','completed','failed','interrupted')),
    document_ids TEXT NOT NULL, image_ids TEXT NOT NULL, citation_language TEXT NOT NULL,
    created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, error_code TEXT,
    run_settings TEXT, run_receipt TEXT
)"""

_PREFERENCES_SQL = """CREATE TABLE IF NOT EXISTS app_preferences (
    name TEXT PRIMARY KEY, value TEXT NOT NULL
)"""


@dataclass(frozen=True)
class ResearchJob:
    job_id: str
    session_id: str
    question: str
    revision: int
    state: str
    document_ids: tuple[str, ...]
    image_ids: tuple[str, ...]
    citation_language: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_code: str | None = None
    run_settings: RunSettings | None = None
    run_receipt: dict | None = None


def _job(row: sqlite3.Row) -> ResearchJob:
    values = {name: (tuple(json.loads(row[name])) if name in {"image_ids", "document_ids"}
                    else row[name]) for name in ResearchJob.__dataclass_fields__}
    values["run_settings"] = RunSettings.from_dict(json.loads(row["run_settings"])) if row["run_settings"] else None
    values["run_receipt"] = json.loads(row["run_receipt"]) if row["run_receipt"] else None
    return ResearchJob(**values)


def _receipt_json(receipt: dict) -> str:
    """Persist counters only; raw provider bodies and arbitrary fields have no slot."""
    invalid = SessionStoreError("invalid_run_receipt")
    if (not isinstance(receipt, dict)
            or set(receipt) - {"requests", "estimated_cost_usd", "actual_billed_usd"}
            or not isinstance(receipt.get("requests"), list) or len(receipt["requests"]) > 40):
        raise invalid
    for field in ("estimated_cost_usd", "actual_billed_usd"):
        value = receipt.get(field)
        if value is not None and (type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1e9):
            raise invalid
    text_fields = {
        "role": {"research", "answer"},
        "reasoning": {None, "none", "minimal", "low", "medium", "high", "xhigh", "max"},
        "backend": {"chatgpt_plan", "openai", "openrouter"},
        "requested_service_tier": {None, "default", "fast", "priority", "flex", "auto"},
        "returned_service_tier": {None, "default", "fast", "priority", "flex", "auto", "scale"},
    }
    counter_fields = {"input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens"}
    for row in receipt["requests"]:
        if not isinstance(row, dict) or set(row) - (set(text_fields) | counter_fields | {"model", "returned_model", "provider", "reported_cost_usd"}):
            raise invalid
        for field, allowed in text_fields.items():
            if field in row and (not isinstance(row[field], (str, type(None))) or row[field] not in allowed):
                raise invalid
        for field in ("model", "returned_model"):
            value = row.get(field)
            if value is not None and not (valid_model_identifier(value, "api") or valid_model_identifier(value, "openrouter")):
                raise invalid
        provider = row.get("provider")
        if provider is not None and (not isinstance(provider, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9 ._/-]{0,79}", provider)):
            raise invalid
        cost = row.get("reported_cost_usd")
        if cost is not None and (type(cost) not in {int, float} or not math.isfinite(cost) or not 0 <= cost <= 1e9):
            raise invalid
        for field in counter_fields:
            value = row.get(field)
            if value is not None and (type(value) is not int or not 0 <= value <= 10**12):
                raise invalid
    return json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _load_images(connection: sqlite3.Connection, session_id: str) -> tuple[SessionImage, ...]:
    rows = connection.execute("SELECT image_id, filename, media_type, byte_length, sha256, created_at, "
                              "width, height, original_image FROM session_images WHERE session_id = ? "
                              "ORDER BY length(image_id), image_id", (session_id,)).fetchall()
    images = tuple(SessionImage(**dict(row)) for row in rows)
    _require([image.image_id for image in images] == [f"I{index}" for index in range(1, len(images) + 1)])
    return images

_DOCUMENTS_SQL = """CREATE TABLE IF NOT EXISTS session_documents (
    session_id TEXT NOT NULL, document_id TEXT NOT NULL, filename TEXT NOT NULL,
    media_type TEXT NOT NULL, byte_length INTEGER NOT NULL, sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL, page_count INTEGER NOT NULL, text_character_count INTEGER NOT NULL,
    textless_page_count INTEGER NOT NULL, original_pdf BLOB NOT NULL, pages_json TEXT NOT NULL,
    PRIMARY KEY (session_id, document_id), UNIQUE (session_id, sha256)
)"""


def _load_documents(connection: sqlite3.Connection, session_id: str) -> tuple[SessionDocument, ...]:
    rows = connection.execute(
        "SELECT document_id, filename, media_type, byte_length, sha256, created_at, page_count, "
        "text_character_count, textless_page_count, original_pdf, pages_json "
        "FROM session_documents WHERE session_id = ? ORDER BY length(document_id), document_id",
        (session_id,),
    ).fetchall()
    documents = []
    for row in rows:
        pages = json.loads(row["pages_json"])
        _require(isinstance(pages, list) and bool(DOCUMENT_ID.fullmatch(row["document_id"])))
        blob = row["original_pdf"]
        if isinstance(blob, memoryview):
            blob = blob.tobytes()
        _require(isinstance(blob, bytes))
        documents.append(SessionDocument(
            row["document_id"], row["filename"], row["media_type"], row["byte_length"], row["sha256"],
            row["created_at"], row["page_count"], row["text_character_count"], row["textless_page_count"],
            tuple(pages), blob,
        ))
    _require([item.document_id for item in documents] == [f"D{index}" for index in range(1, len(documents) + 1)])
    return tuple(documents)


class SQLiteSessionStore:
    """One versioned local SQLite store; operations own short, closed connections.

    Metadata and one complete product snapshot share a row, so a revision-checked
    transaction cannot advance only part of a completed turn. No indexes or traces
    from research are stored. This is local plaintext data, not cloud account state.
    """

    SCHEMA_VERSION = 4

    def __init__(self, path: str | Path | None = None) -> None:
        try:
            self.path = Path(path if path is not None else default_session_path()).expanduser().resolve()
        except (OSError, ValueError, RuntimeError):
            raise SessionStoreError() from None

    @contextmanager
    def _transaction(self):
        connection = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                if connection.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone():
                    raise SessionStoreError("incompatible_session_store")
                connection.execute(_SESSIONS_SQL)
                connection.execute(_DOCUMENTS_SQL)
                connection.execute(_IMAGES_SQL)
                connection.execute(_JOBS_SQL)
                connection.execute(_PREFERENCES_SQL)
                connection.execute("CREATE UNIQUE INDEX one_active_research_job ON research_jobs(session_id) "
                                   "WHERE state IN ('queued', 'researching')")
                connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
            elif version in {1, 2}:
                # Additive only. Existing session payloads are not rewritten.
                connection.execute(_DOCUMENTS_SQL)
                connection.execute("ALTER TABLE sessions ADD COLUMN citation_language TEXT NOT NULL DEFAULT 'en'")
                connection.execute(_IMAGES_SQL)
                connection.execute(_JOBS_SQL)
                connection.execute(_PREFERENCES_SQL)
                connection.execute("CREATE UNIQUE INDEX one_active_research_job ON research_jobs(session_id) "
                                   "WHERE state IN ('queued', 'researching')")
                connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
            elif version == 3:
                # Unknown historical runtime configuration remains NULL. Preserve
                # every session payload, attachment, citation and job identity.
                connection.execute("ALTER TABLE research_jobs ADD COLUMN run_settings TEXT")
                connection.execute("ALTER TABLE research_jobs ADD COLUMN run_receipt TEXT")
                connection.execute(_PREFERENCES_SQL)
                connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")
            elif version != self.SCHEMA_VERSION:
                raise SessionStoreError("incompatible_session_store")
            yield connection
            connection.commit()
        except SessionStoreError:
            raise
        except (sqlite3.Error, OSError):
            raise SessionStoreError() from None
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, RunError):
            raise SessionStoreError("invalid_session_data") from None
        finally:
            # close() rolls back an uncommitted transaction, including commit failures.
            if connection is not None:
                try:
                    connection.close()
                except sqlite3.Error:
                    raise SessionStoreError() from None

    def create(self, title: str = "") -> StoredSession:
        with self._transaction() as connection:
            _require(isinstance(title, str))
            now = datetime.now(timezone.utc).isoformat()
            metadata = SessionMetadata(uuid4().hex, now, now, title, 0)
            state = SessionState()
            connection.execute("INSERT INTO sessions (session_id,created_at,updated_at,title,revision,payload) "
                               "VALUES (?, ?, ?, ?, ?, ?)",
                               (metadata.session_id, now, now, title, 0, _encode(state)))
        return StoredSession(metadata, state, ())

    @staticmethod
    def _load(connection: sqlite3.Connection, session_id: str) -> StoredSession:
        row = connection.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise SessionStoreError("session_not_found")
        metadata = _metadata(row)
        documents = _load_documents(connection, session_id)
        images = _load_images(connection, session_id)
        return StoredSession(metadata, _decode(row["payload"], metadata.revision, documents, images), documents, images)

    def load(self, session_id: str) -> StoredSession:
        with self._transaction() as connection:
            snapshot = self._load(connection, session_id)
        return snapshot

    def list_sessions(self) -> tuple[SessionMetadata, ...]:
        with self._transaction() as connection:
            rows = connection.execute("SELECT session_id, created_at, updated_at, title, revision, citation_language "
                                      "FROM sessions ORDER BY updated_at DESC, session_id").fetchall()
            metadata = tuple(_metadata(row) for row in rows)
        return metadata

    def commit(self, session_id: str, revision: int, state: SessionState) -> SessionMetadata:
        with self._transaction() as connection:
            metadata = self._commit(connection, session_id, revision, state)
        return metadata

    def _commit(self, connection: sqlite3.Connection, session_id: str, revision: int,
                state: SessionState) -> SessionMetadata:
        current = self._load(connection, session_id)
        if current.metadata.revision != revision:
            raise SessionConflictError()
        _require(len(state.turns) == revision + 1 and state.turns[:-1] == current.state.turns)
        _require(state.acquisitions[:len(current.state.acquisitions)] == current.state.acquisitions)
        documents = _load_documents(connection, session_id)
        payload = _encode(state, documents, current.images)
        # A clock adjustment must not invalidate otherwise valid saved metadata.
        now = max(current.metadata.updated_at, datetime.now(timezone.utc).isoformat())
        title = current.metadata.title or " ".join(state.turns[0].question.split())[:100]
        metadata = SessionMetadata(session_id, current.metadata.created_at, now, title, revision + 1,
                                   current.metadata.citation_language)
        updated = connection.execute(
            "UPDATE sessions SET updated_at = ?, title = ?, revision = ?, payload = ? "
            "WHERE session_id = ? AND revision = ?",
            (now, title, revision + 1, payload, session_id, revision),
        )
        if updated.rowcount != 1:
            raise SessionConflictError()
        return metadata

    def rename(self, session_id: str, title: str) -> SessionMetadata:
        """Edit metadata only; the completed-turn revision and payload are untouched."""
        with self._transaction() as connection:
            if not isinstance(title, str) or not title.strip():
                raise SessionStoreError("invalid_session_title")
            current = self._load(connection, session_id).metadata
            now = max(current.updated_at, datetime.now(timezone.utc).isoformat())
            title = title.strip()
            connection.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                               (title, now, session_id))
            metadata = SessionMetadata(session_id, current.created_at, now, title, current.revision,
                                       current.citation_language)
        return metadata

    def delete(self, session_id: str, *, revision: int | None = None) -> None:
        """Permanently remove one session; optionally guard a displayed turn count."""
        with self._transaction() as connection:
            current = self._load(connection, session_id)
            self._require_idle(connection, session_id)
            if revision is not None and current.metadata.revision != revision:
                raise SessionConflictError()
            connection.execute("DELETE FROM session_documents WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM session_images WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM research_jobs WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def attach_document(self, session_id: str, revision: int, filename: str,
                        media_type: str, data: bytes) -> AttachedDocument:
        """Store one PDF without creating a turn or advancing the completed-turn revision."""
        prepared = prepare_pdf(filename, media_type, data)
        with self._transaction() as connection:
            current = self._load(connection, session_id)
            self._require_idle(connection, session_id)
            if current.metadata.revision != revision:
                raise SessionConflictError()
            existing = connection.execute(
                "SELECT document_id FROM session_documents WHERE session_id = ? AND sha256 = ?",
                (session_id, prepared.sha256),
            ).fetchone()
            if existing is not None:
                document = next(item for item in current.documents if item.document_id == existing["document_id"])
                return AttachedDocument(document, False)
            numbers = [int(item.document_id[1:]) for item in current.documents]
            document_id = f"D{max(numbers, default=0) + 1}"
            _require(bool(DOCUMENT_ID.fullmatch(document_id)))
            created_at = datetime.now(timezone.utc).isoformat()
            document = SessionDocument(
                document_id, prepared.filename, prepared.media_type, prepared.byte_length, prepared.sha256,
                created_at, prepared.page_count, prepared.text_character_count, prepared.textless_page_count,
                prepared.pages, prepared.original_pdf,
            )
            connection.execute(
                "INSERT INTO session_documents (session_id, document_id, filename, media_type, byte_length, "
                "sha256, created_at, page_count, text_character_count, textless_page_count, original_pdf, pages_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, document.document_id, document.filename, document.media_type, document.byte_length,
                 document.sha256, document.created_at, document.page_count, document.text_character_count,
                 document.textless_page_count, document.original_pdf,
                 json.dumps(list(document.pages), ensure_ascii=False, separators=(",", ":"))),
            )
            now = max(current.metadata.updated_at, created_at)
            updated = connection.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ? AND revision = ?",
                (now, session_id, revision),
            )
            if updated.rowcount != 1:
                raise SessionConflictError()
        return AttachedDocument(document, True)

    @staticmethod
    def _require_idle(connection: sqlite3.Connection, session_id: str) -> None:
        if connection.execute("SELECT 1 FROM research_jobs WHERE session_id = ? "
                              "AND state IN ('queued','researching')", (session_id,)).fetchone():
            raise SessionStoreError("session_busy")

    def set_citation_language(self, session_id: str, language: str) -> SessionMetadata:
        if language not in CITATION_LANGUAGES:
            raise SessionStoreError("invalid_citation_language")
        with self._transaction() as connection:
            self._load(connection, session_id)
            connection.execute("UPDATE sessions SET citation_language = ? WHERE session_id = ?",
                               (language, session_id))
            return self._load(connection, session_id).metadata

    @staticmethod
    def _insert_document(connection: sqlite3.Connection, session_id: str,
                         prepared: PreparedDocument) -> str:
        existing = connection.execute("SELECT document_id FROM session_documents WHERE session_id=? AND sha256=?",
                                      (session_id, prepared.sha256)).fetchone()
        if existing:
            return existing["document_id"]
        count = connection.execute("SELECT count(*) FROM session_documents WHERE session_id=?", (session_id,)).fetchone()[0]
        document_id = f"D{count + 1}"
        connection.execute("INSERT INTO session_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (session_id, document_id, prepared.filename, prepared.media_type, prepared.byte_length,
                            prepared.sha256, datetime.now(timezone.utc).isoformat(), prepared.page_count,
                            prepared.text_character_count, prepared.textless_page_count, prepared.original_pdf,
                            json.dumps(list(prepared.pages), ensure_ascii=False, separators=(",", ":"))))
        return document_id

    @staticmethod
    def _insert_image(connection: sqlite3.Connection, session_id: str, prepared: PreparedImage) -> str:
        existing = connection.execute("SELECT image_id FROM session_images WHERE session_id=? AND sha256=?",
                                      (session_id, prepared.sha256)).fetchone()
        if existing:
            return existing["image_id"]
        count = connection.execute("SELECT count(*) FROM session_images WHERE session_id=?", (session_id,)).fetchone()[0]
        image_id = f"I{count + 1}"
        connection.execute("INSERT INTO session_images VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (session_id, image_id, prepared.filename, prepared.media_type, prepared.byte_length,
                            prepared.sha256, datetime.now(timezone.utc).isoformat(), prepared.width, prepared.height,
                            prepared.original_image))
        return image_id

    def accept_job(self, question: str, *, idempotency_key: str, session_id: str | None = None,
                   revision: int = 0, documents: tuple[PreparedDocument, ...] = (),
                   images: tuple[PreparedImage, ...] = (), retained_image_ids: tuple[str, ...] = (),
                   citation_language: str | None = None, capacity: int = 10,
                   run_settings: RunSettings | None = None, remember_settings: bool = True) -> ResearchJob:
        """Atomically accept a question, its validated files, and its durable identity.

        Validation/decode happens before this short transaction. Invalid admission
        rolls back even a newly allocated session and every inserted attachment.
        """
        if not isinstance(question, str) or not question.strip() or len(question) > 20000:
            raise SessionStoreError("invalid_question")
        if not isinstance(idempotency_key, str) or not 16 <= len(idempotency_key) <= 256:
            raise SessionStoreError("invalid_submission_key")
        if citation_language is not None and citation_language not in CITATION_LANGUAGES:
            raise SessionStoreError("invalid_citation_language")
        if run_settings is not None and not isinstance(run_settings, RunSettings):
            raise SessionStoreError("invalid_run_settings")
        settings_json = json.dumps(run_settings.to_dict(), sort_keys=True) if run_settings is not None else None
        if len(documents) + len(images) + len(retained_image_ids) > MAX_ATTACHMENTS_PER_QUESTION:
            raise SessionStoreError("attachment_count_exceeded")
        if sum(item.byte_length for item in (*documents, *images)) > MAX_ATTACHMENT_REQUEST_BYTES:
            raise SessionStoreError("attachment_request_too_large")
        question = question.strip()
        fingerprint_values = [session_id, revision, question, [d.sha256 for d in documents], [i.sha256 for i in images],
                              list(retained_image_ids), citation_language]
        if run_settings is not None:
            fingerprint_values.append(run_settings.to_dict())
        fingerprint = hashlib.sha256(json.dumps(fingerprint_values,
            separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        with self._transaction() as connection:
            old = connection.execute("SELECT * FROM research_jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise SessionStoreError("submission_conflict")
                return _job(old)
            active = connection.execute("SELECT count(*) FROM research_jobs WHERE state IN ('queued','researching')").fetchone()[0]
            if active >= capacity:
                raise SessionStoreError("research_queue_full")
            now = datetime.now(timezone.utc).isoformat()
            if session_id is None:
                if revision != 0:
                    raise SessionConflictError()
                session_id = uuid4().hex
                title = " ".join(question.split())[:100]
                connection.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
                                   (session_id, now, now, title, 0, _encode(SessionState()), citation_language or "en"))
            saved = self._load(connection, session_id)
            if saved.metadata.revision != revision:
                raise SessionConflictError()
            self._require_idle(connection, session_id)
            if (len(set(retained_image_ids)) != len(retained_image_ids)
                    or not set(retained_image_ids) <= {i.image_id for i in saved.images}):
                raise SessionStoreError("invalid_image_selection")
            retained_bytes = sum(image.byte_length for image in saved.images if image.image_id in retained_image_ids)
            if retained_bytes + sum(item.byte_length for item in (*documents, *images)) > MAX_ATTACHMENT_REQUEST_BYTES:
                raise SessionStoreError("attachment_request_too_large")
            document_ids = tuple(dict.fromkeys(self._insert_document(connection, session_id, d) for d in documents))
            image_ids = tuple(dict.fromkeys((*retained_image_ids,
                                            *(self._insert_image(connection, session_id, i) for i in images))))
            # Reconstruct and validate custody before acceptance becomes durable.
            self._load(connection, session_id)
            language = citation_language or saved.metadata.citation_language
            connection.execute("UPDATE sessions SET citation_language=?, updated_at=? WHERE session_id=?",
                               (language, max(now, saved.metadata.updated_at), session_id))
            job_id = uuid4().hex
            connection.execute("INSERT INTO research_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                               (job_id, session_id, idempotency_key, fingerprint, question, revision, "queued",
                                json.dumps(document_ids), json.dumps(image_ids), language, now, None, None, None,
                                settings_json, None))
            if settings_json is not None and remember_settings:
                self._remember_run_settings(connection, run_settings, settings_json)
            return _job(connection.execute("SELECT * FROM research_jobs WHERE job_id=?", (job_id,)).fetchone())

    def get_run_settings(self) -> RunSettings | None:
        """Last-used UI preferences, independent of every accepted job snapshot."""
        with self._transaction() as connection:
            row = connection.execute("SELECT value FROM app_preferences WHERE name='run_settings'").fetchone()
            return RunSettings.from_dict(json.loads(row["value"])) if row else None

    def set_run_settings(self, settings: RunSettings) -> None:
        if not isinstance(settings, RunSettings):
            raise SessionStoreError("invalid_run_settings")
        with self._transaction() as connection:
            encoded = json.dumps(settings.to_dict(), sort_keys=True)
            self._remember_run_settings(connection, settings, encoded)

    @staticmethod
    def _remember_run_settings(connection, settings: RunSettings, encoded: str) -> None:
        # Preserve a legacy single preference before another backend replaces it.
        previous = connection.execute("SELECT value FROM app_preferences WHERE name='run_settings'").fetchone()
        if previous:
            old = RunSettings.from_dict(json.loads(previous["value"]))
            connection.execute("INSERT INTO app_preferences(name,value) VALUES (?,?) ON CONFLICT(name) DO NOTHING",
                               ("run_settings:" + old.backend, previous["value"]))
        connection.executemany("INSERT INTO app_preferences(name,value) VALUES (?,?) "
                               "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                               [("run_settings", encoded), ("run_settings:" + settings.backend, encoded)])

    def get_run_settings_profiles(self) -> dict[str, RunSettings]:
        """Retain exact last-used role/tier choices separately for each backend."""
        with self._transaction() as connection:
            rows = connection.execute("SELECT name,value FROM app_preferences WHERE name IN (?,?,?,?)",
                                      ("run_settings", "run_settings:chatgpt_plan", "run_settings:openai",
                                       "run_settings:openrouter")).fetchall()
        profiles = {}
        for row in rows:
            settings = RunSettings.from_dict(json.loads(row["value"]))
            if row["name"] == "run_settings":
                profiles.setdefault(settings.backend, settings)
            elif row["name"] == "run_settings:" + settings.backend:
                profiles[settings.backend] = settings
        return profiles

    def get_billing_authorizations(self) -> dict[str, bool]:
        """Trusted-local preferences; absent or malformed values never authorize."""
        with self._transaction() as connection:
            rows = dict(connection.execute("SELECT name,value FROM app_preferences WHERE name IN (?,?)",
                                           tuple("billing_authorized:" + backend for backend in sorted(BILLED_BACKENDS))))
        return {backend: rows.get("billing_authorized:" + backend) == "true" for backend in sorted(BILLED_BACKENDS)}

    def set_billing_authorization(self, backend: str, authorized: bool) -> None:
        if type(backend) is not str or backend not in BILLED_BACKENDS or type(authorized) is not bool:
            raise SessionStoreError("invalid_billing_authorization")
        with self._transaction() as connection:
            connection.execute("INSERT INTO app_preferences(name,value) VALUES (?,?) "
                               "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                               ("billing_authorized:" + backend, json.dumps(authorized)))

    def save_run_receipt(self, job_id: str, receipt: dict) -> None:
        """Attach optional safe usage once; a historical receipt is never rewritten."""
        encoded = _receipt_json(receipt)
        with self._transaction() as connection:
            row = connection.execute("SELECT run_receipt FROM research_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise SessionStoreError("job_not_found")
            if row["run_receipt"] is not None and row["run_receipt"] != encoded:
                raise SessionStoreError("run_receipt_conflict")
            connection.execute("UPDATE research_jobs SET run_receipt=? WHERE job_id=? AND run_receipt IS NULL",
                               (encoded, job_id))

    def get_job(self, job_id: str) -> ResearchJob:
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM research_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise SessionStoreError("job_not_found")
            return _job(row)

    def find_submission(self, idempotency_key: str) -> ResearchJob | None:
        """Resolve an explicitly replayed form to its accepted local run."""
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM research_jobs WHERE idempotency_key=?",
                                     (idempotency_key,)).fetchone()
            return _job(row) if row else None

    def list_jobs(self, session_id: str | None = None) -> tuple[ResearchJob, ...]:
        with self._transaction() as connection:
            rows = connection.execute("SELECT * FROM research_jobs " + ("WHERE session_id=? " if session_id else "")
                                      + "ORDER BY created_at DESC, job_id DESC", (session_id,) if session_id else ()).fetchall()
            return tuple(_job(row) for row in rows)

    def claim_next_job(self) -> ResearchJob | None:
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM research_jobs WHERE state='queued' ORDER BY created_at, job_id LIMIT 1").fetchone()
            if row is None:
                return None
            connection.execute("UPDATE research_jobs SET state='researching',started_at=? WHERE job_id=? AND state='queued'",
                               (datetime.now(timezone.utc).isoformat(), row["job_id"]))
            return _job(connection.execute("SELECT * FROM research_jobs WHERE job_id=?", (row["job_id"],)).fetchone())

    def commit_job(self, job_id: str, session_id: str, revision: int, state: SessionState,
                   *, run_receipt: dict | None = None) -> SessionMetadata:
        try:
            encoded_receipt = _receipt_json(run_receipt) if run_receipt is not None else None
        except SessionStoreError:
            # Invalid optional reporting is unknown; the validated answer and
            # immutable configuration still commit normally. No raw data is saved.
            encoded_receipt = None
        with self._transaction() as connection:
            row = connection.execute("SELECT * FROM research_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None or row["state"] != "researching" or (row["session_id"], row["revision"]) != (session_id, revision):
                raise SessionConflictError()
            _require(state.turns[-1].question == row["question"])
            _require(set(json.loads(row["image_ids"])) <= set(state.turns[-1].image_ids))
            metadata = self._commit(connection, session_id, revision, state)
            connection.execute("UPDATE research_jobs SET state='completed',finished_at=?, "
                               "run_receipt=COALESCE(run_receipt,?) WHERE job_id=?",
                               (datetime.now(timezone.utc).isoformat(), encoded_receipt, job_id))
            return metadata

    def fail_job(self, job_id: str, code: str = "research_failed") -> None:
        allowed = {"research_failed", "session_conflict", "model_image_input_unsupported",
                   "model_configuration_missing", "model_request_rejected", "model_authentication_failed",
                   "model_access_denied", "model_unavailable", "model_rate_limited", "model_transport_failed",
                   "model_request_timed_out", "model_backend_incompatible", "model_reasoning_unsupported",
                   "model_not_supported", "malformed_model_response", "model_response_incomplete",
                   "model_response_incomplete_content_filter", "model_response_incomplete_max_output_tokens",
                   "model_catalog_unavailable", "model_identifier_invalid", "model_contract_incompatible",
                   "model_routing_mismatch", "paid_inference_authorization_required",
                   "historical_run_settings_unknown"}
        with self._transaction() as connection:
            connection.execute("UPDATE research_jobs SET state='failed',finished_at=?,error_code=? "
                               "WHERE job_id=? AND state IN ('queued','researching')",
                               (datetime.now(timezone.utc).isoformat(), code if code in allowed else "research_failed", job_id))

    def interrupt_jobs(self, code: str = "server_interrupted") -> None:
        """Startup/shutdown recovery never dispatches a persisted paid operation."""
        code = code if code in {"server_interrupted", "storage_interrupted"} else "server_interrupted"
        with self._transaction() as connection:
            connection.execute("UPDATE research_jobs SET state='interrupted',finished_at=?,error_code=? "
                               "WHERE state IN ('queued','researching')", (datetime.now(timezone.utc).isoformat(), code))
