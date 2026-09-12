"""Local session custody, serialization and transactions; no semantic decisions."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from scryraven.presentation import Citation, CitationUse
from scryraven.research import Analysis, RunError, _validate_analysis
from scryraven.sources import Evidence, exact_view


@dataclass(frozen=True)
class SessionTurn:
    """Completed public answer and its exact presentation snapshot, without traces."""

    question: str
    answer: str
    analysis: Analysis
    posture: str
    stop_reason: str
    selected_evidence: tuple[Evidence, ...] = ()
    citations: tuple[Citation, ...] = ()
    citation_uses: tuple[CitationUse, ...] = ()


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


@dataclass(frozen=True)
class StoredSession:
    metadata: SessionMetadata
    state: SessionState


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


class _CitationRecord(_Record):
    number: int
    source_id: str
    title: str
    url: str
    material_ids: list[str]


class _UseRecord(_Record):
    number: int
    start: int
    end: int


class _TurnRecord(_Record):
    question: str
    answer: str
    analysis: Analysis
    posture: Literal["supported", "partial", "unable"]
    stop_reason: Literal["supported", "not_established", "research_bound", "navigation_bound"]
    selected_evidence: list[_EvidenceRecord]
    citations: list[_CitationRecord]
    citation_uses: list[_UseRecord]


class _StateRecord(_Record):
    turns: list[_TurnRecord]
    acquisitions: list[_EvidenceRecord]


class _MetadataRecord(_Record):
    session_id: str
    created_at: str
    updated_at: str
    title: str
    revision: int


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid_session_data")


def _metadata(row: sqlite3.Row) -> SessionMetadata:
    record = _MetadataRecord.model_validate({name: row[name] for name in _MetadataRecord.model_fields})
    _require(len(record.session_id) == 32 and all(c in "0123456789abcdef" for c in record.session_id))
    created, updated = datetime.fromisoformat(record.created_at), datetime.fromisoformat(record.updated_at)
    _require(created.tzinfo is not None and updated.tzinfo is not None and updated >= created)
    _require(record.revision >= 0)
    return SessionMetadata(**record.model_dump())


def _evidence(record: _EvidenceRecord) -> Evidence:
    _require(bool(record.id and record.source_id and record.url.strip() and record.content.strip()))
    return Evidence(**record.model_dump())


def _decode(payload: str, revision: int) -> SessionState:
    record = _StateRecord.model_validate_json(payload)
    _require(len(record.turns) == revision)
    acquisitions = tuple(_evidence(item) for item in record.acquisitions)
    by_id = {item.id: item for item in acquisitions}
    by_url: dict[str, str] = {}
    for index, item in enumerate(acquisitions, 1):
        # The existing allocator uses corpus length. Validate its invariant, never
        # repair or renumber IDs on load, including same-URL acquisition versions.
        _require(item.id == f"E{index}" and item.acquisition != "targeted_view")
        _require(item.source_id == by_url.setdefault(item.url, item.id))
    _require(bool(record.turns) or not acquisitions)
    turns = []
    for saved in record.turns:
        _require(bool(saved.question.strip() and saved.answer.strip()))
        selected = tuple(_evidence(item) for item in saved.selected_evidence)
        materials = {item.id: item for item in selected}
        _require(len(materials) == len(selected))
        for item in selected:
            if item.acquisition == "targeted_view":
                parent = by_id[item.parent_id]
                _require(item == exact_view(parent, item.start_char, item.end_char))
            else:
                _require(by_id[item.id] == item)
        analysis = saved.analysis
        original = analysis.model_dump()
        _validate_analysis(analysis, list(acquisitions), [])
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
        citations = tuple(Citation(c.number, c.source_id, c.title, c.url,
                                   tuple(materials[ref] for ref in c.material_ids)) for c in saved.citations)
        _require(len({c.source_id for c in citations}) == len(citations))
        for number, citation in enumerate(citations, 1):
            source = by_id[citation.source_id]
            _require(citation.number == number and source.id == source.source_id)
            _require((citation.title, citation.url) == (source.title, source.url))
            _require(bool(citation.materials) and citation.materials == tuple(
                item for item in selected if item.source_id == citation.source_id))
        uses = tuple(CitationUse(**item.model_dump()) for item in saved.citation_uses)
        end = 0
        for use in uses:
            _require(1 <= use.number <= len(citations) and end <= use.start < use.end <= len(saved.answer))
            _require(saved.answer[use.start:use.end] == f"[{use.number}]")
            end = use.end
        _require(list(dict.fromkeys(use.number for use in uses)) == list(range(1, len(citations) + 1)))
        _require(bool(citations) == bool(selected))
        turns.append(SessionTurn(saved.question, saved.answer, analysis, saved.posture, saved.stop_reason,
                                 selected, citations, uses))
    return SessionState(tuple(turns), acquisitions)


def _encode(state: SessionState) -> str:
    # Citation material references resolve only against this turn's saved packet.
    turns = []
    for turn in state.turns:
        turns.append({
            "question": turn.question, "answer": turn.answer, "analysis": turn.analysis.model_dump(),
            "posture": turn.posture, "stop_reason": turn.stop_reason,
            "selected_evidence": [asdict(item) for item in turn.selected_evidence],
            "citations": [{"number": c.number, "source_id": c.source_id, "title": c.title, "url": c.url,
                           "material_ids": [item.id for item in c.materials]} for c in turn.citations],
            "citation_uses": [asdict(item) for item in turn.citation_uses],
        })
    payload = json.dumps({"turns": turns, "acquisitions": [asdict(item) for item in state.acquisitions]},
                         ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    _require(_decode(payload, len(state.turns)) == state)
    return payload


class SQLiteSessionStore:
    """One versioned local SQLite store; operations own short, closed connections.

    Metadata and one complete product snapshot share a row, so a revision-checked
    transaction cannot advance only part of a completed turn. No indexes or traces
    from research are stored. This is local plaintext data, not cloud account state.
    """

    SCHEMA_VERSION = 1

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
                connection.execute("""CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    title TEXT NOT NULL, revision INTEGER NOT NULL CHECK (revision >= 0), payload TEXT NOT NULL
                )""")
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
            connection.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
                               (*asdict(metadata).values(), _encode(state)))
        return StoredSession(metadata, state)

    @staticmethod
    def _load(connection: sqlite3.Connection, session_id: str) -> StoredSession:
        row = connection.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            raise SessionStoreError("session_not_found")
        metadata = _metadata(row)
        return StoredSession(metadata, _decode(row["payload"], metadata.revision))

    def load(self, session_id: str) -> StoredSession:
        with self._transaction() as connection:
            snapshot = self._load(connection, session_id)
        return snapshot

    def list_sessions(self) -> tuple[SessionMetadata, ...]:
        with self._transaction() as connection:
            rows = connection.execute("SELECT session_id, created_at, updated_at, title, revision "
                                      "FROM sessions ORDER BY updated_at DESC, session_id").fetchall()
            metadata = tuple(_metadata(row) for row in rows)
        return metadata

    def commit(self, session_id: str, revision: int, state: SessionState) -> SessionMetadata:
        with self._transaction() as connection:
            current = self._load(connection, session_id)
            if current.metadata.revision != revision:
                raise SessionConflictError()
            _require(len(state.turns) == revision + 1 and state.turns[:-1] == current.state.turns)
            _require(state.acquisitions[:len(current.state.acquisitions)] == current.state.acquisitions)
            payload = _encode(state)
            # A clock adjustment must not invalidate otherwise valid saved metadata.
            now = max(current.metadata.updated_at, datetime.now(timezone.utc).isoformat())
            title = current.metadata.title or " ".join(state.turns[0].question.split())[:100]
            metadata = SessionMetadata(session_id, current.metadata.created_at, now, title, revision + 1)
            updated = connection.execute(
                "UPDATE sessions SET updated_at = ?, title = ?, revision = ?, payload = ? "
                "WHERE session_id = ? AND revision = ?",
                (now, title, revision + 1, payload, session_id, revision),
            )
            if updated.rowcount != 1:
                raise SessionConflictError()
        return metadata
