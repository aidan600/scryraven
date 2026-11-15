"""Storage and delivery guarantees for owner-scoped Reading Room activity."""

import json
import sqlite3
from contextlib import closing
from threading import Event

import pytest
from test_persistent_sessions import tmp_path as external_tmp_path

from scryraven.activity_journal import MAX_ACTIVITY_EVENTS, ActivityJournal
from scryraven.session_store import MAX_ACTIVITY_BYTES, SessionStoreError, SQLiteSessionStore

tmp_path = external_tmp_path
ALICE = "alice@example.test"


def admit(store, *, owner_id=None):
    return store.accept_job("Research question", idempotency_key="test-activity-journal", owner_id=owner_id)


def snapshot(journal, job, *, owner_id=None, after=0):
    return journal.read(job.session_id, job.job_id, owner_id=owner_id, after=after)


def test_schema_seven_upgrade_keeps_existing_rows_and_history_is_optional(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    job = admit(store, owner_id=ALICE)
    with closing(sqlite3.connect(store.path)) as connection:
        connection.execute("DROP TABLE research_job_activity")
        connection.execute("PRAGMA user_version=7")
        connection.commit()
        before = [connection.execute(f"SELECT * FROM {table}").fetchall() for table in ("sessions", "research_jobs")]

    # A missing activity table must not prevent an authorized status lookup.
    assert snapshot(ActivityJournal(store), job, owner_id=ALICE)["state"] == "queued"
    assert store.get_job(job.job_id) == job
    with closing(sqlite3.connect(store.path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 8
        after = [connection.execute(f"SELECT * FROM {table}").fetchall() for table in ("sessions", "research_jobs")]
    assert before == after
    assert not snapshot(ActivityJournal(store), job, owner_id=ALICE)["available"]


def test_strict_job_session_and_owner_scope_applies_to_live_and_saved_events(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    job = admit(store, owner_id=ALICE)
    other_session = store.create(owner_id=ALICE).metadata.session_id
    store.save_job_activity_batch(((job.job_id, 1, json.dumps([{"type": "test", "seq": 1}])),))
    journal = ActivityJournal(store)
    assert snapshot(journal, job, owner_id=ALICE)["cursor"] == 1
    for session_id, owner_id in ((other_session, ALICE), (job.session_id, None),
                                 (job.session_id, "bob@example.test"), (job.session_id, "admin@example.test")):
        with pytest.raises(SessionStoreError, match="job_not_found"):
            journal.read(session_id, job.job_id, owner_id=owner_id)


def test_bounded_publication_reports_evicted_and_ahead_cursors(tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    job = admit(store)
    journal = ActivityJournal(store)
    monkeypatch.setattr(journal, "_start_writer", lambda: None)
    publish = journal.publisher(job.job_id, session_id=job.session_id)
    for _ in range(MAX_ACTIVITY_EVENTS + 10):
        publish({"type": "search", "activity_id": "1:group:1", "prompt": "private"})
    result = snapshot(journal, job, after=1)
    assert result["truncated"] and result["reset"]
    assert result["first_cursor"] == 11
    assert len(result["events"]) == MAX_ACTIVITY_EVENTS
    assert result["last_event"]["activity_id"] == "1:group:1"
    assert "prompt" not in result["last_event"]
    assert snapshot(journal, job, after=result["cursor"])["events"] == []
    assert snapshot(journal, job, after=result["cursor"] + 1)["reset"]

    # Independent byte cap, including the enclosing JSON and metadata.
    publish({"type": "search", "operations": [{"query": "a" * (MAX_ACTIVITY_BYTES // 2)}]})
    publish({"type": "search", "operations": [{"query": "b" * (MAX_ACTIVITY_BYTES // 2)}]})
    result = snapshot(journal, job)
    assert len(result["events"]) == 1 and result["cursor"] == MAX_ACTIVITY_EVENTS + 12
    publish({"type": "search", "operations": [{"query": "c" * MAX_ACTIVITY_BYTES}]})
    assert snapshot(journal, job)["cursor"] == result["cursor"]


def test_live_activity_stays_visible_while_write_is_busy_and_persists_after_recovery(tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    job = admit(store)
    store.claim_next_job()
    journal = ActivityJournal(store)
    pub = journal.publisher(job.job_id, session_id=job.session_id)
    busy, saved = Event(), Event()
    save = store.save_job_activity_batch

    def capture(snapshots):
        try:
            save(snapshots)
        except SessionStoreError:
            busy.set()
            raise
        saved.set()

    monkeypatch.setattr(store, "save_job_activity_batch", capture)
    try:
        with closing(sqlite3.connect(store.path)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            pub({"type": "search", "label": "Searching"})
            assert busy.wait(2)
            live = snapshot(journal, job)
            assert live["state"] == "researching" and live["last_event"]["label"] == "Searching"
            assert not saved.is_set()
        assert saved.wait(3)
        store.interrupt_jobs()
        reopened = snapshot(ActivityJournal(SQLiteSessionStore(store.path)), job)
        assert reopened["state"] == "interrupted" and reopened["last_event"] == live["last_event"]
    finally:
        journal.close()


def test_late_activity_writes_neither_overwrite_newer_history_nor_recreate_deleted_history(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    job = admit(store)
    snapshots = tuple((job.job_id, sequence, json.dumps([{"type": "test", "seq": sequence}])) for sequence in (2, 1))
    store.save_job_activity_batch(snapshots)
    journal = ActivityJournal(store)
    assert snapshot(journal, job)["cursor"] == 2
    store.interrupt_jobs()
    store.delete(job.session_id)
    store.save_job_activity_batch(snapshots)
    with closing(sqlite3.connect(store.path)) as connection:
        assert not connection.execute("SELECT 1 FROM research_job_activity").fetchall()
    with pytest.raises(SessionStoreError, match="job_not_found"):
        snapshot(journal, job)
