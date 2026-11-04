"""Answer comments have independent custody, ownership and append-only answer identity."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import pytest
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_jobs import key, result

from scryraven import session_store
from scryraven.research_jobs import ResearchJobManager
from scryraven.session_store import MAX_ANSWER_FEEDBACK_CHARS, SessionStoreError, SQLiteSessionStore

tmp_path = external_tmp_path
ALICE = "alice@example.test"
BOB = "bob@example.test"


def completed(store, *, owner=ALICE):
    saved = store.create("Existing answer", owner_id=owner)
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    store.commit(saved.metadata.session_id, 0, session_store._decode(payload, 1))
    return store.load(saved.metadata.session_id)


def ordinary_rows(path):
    with closing(sqlite3.connect(path)) as connection:
        return {table: connection.execute(f"SELECT * FROM {table}").fetchall()
                for table in ("sessions", "research_jobs", "session_documents", "session_images", "user_submissions")}


def test_feedback_persists_without_changing_research_rows_or_historical_source_custody(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = completed(store)
    sid = saved.metadata.session_id
    before = ordinary_rows(store.path)
    first = store.add_feedback(sid, 1, "  Useful answer.\nThank you.  ", owner_id=ALICE)
    second = store.add_feedback(sid, 1, "<script>alert('plain text')</script>", owner_id=ALICE)
    reopened = SQLiteSessionStore(store.path)
    assert reopened.list_feedback(sid) == (first, second)
    assert first.text == "Useful answer.\nThank you."
    assert second.text == "<script>alert('plain text')</script>"
    assert first.author_id == second.author_id == ALICE
    assert first.turn_index == second.turn_index == 1
    assert datetime.fromisoformat(first.created_at).utcoffset().total_seconds() == 0
    assert ordinary_rows(store.path) == before
    assert reopened.load(sid) == saved
    reopened.delete_feedback(sid, 1, first.feedback_id, owner_id=ALICE)
    assert store.list_feedback(sid) == (second,)
    assert ordinary_rows(store.path) == before


def test_feedback_remains_on_original_answer_while_followup_research_commits(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = completed(store)
    sid = saved.metadata.session_id
    started, release = Event(), Event()
    seen = []

    def blocked(question, **kwargs):
        seen.append((question, kwargs))
        started.set()
        assert release.wait(10)
        return replace(result(question), evidence=kwargs["retained_acquisitions"])

    manager = ResearchJobManager(store, session_options={"engine": blocked})
    try:
        job = manager.submit("A follow-up", session_id=sid, revision=1,
                             idempotency_key=key(1), owner_id=ALICE, submission_quota=1)
        assert started.wait(5)
        before = ordinary_rows(store.path)
        first = store.add_feedback(sid, 1, "First historical comment", owner_id=ALICE)
        disposable = store.add_feedback(sid, 1, "Remove during research", owner_id=ALICE)
        store.delete_feedback(sid, 1, disposable.feedback_id, owner_id=ALICE)
        assert ordinary_rows(store.path) == before
        with pytest.raises(SessionStoreError, match="feedback_turn_not_found"):
            store.add_feedback(sid, 2, "Answer not finished", owner_id=ALICE)
        release.set()
        assert manager.wait_idle(10)
        assert manager.get(job.job_id).state == "completed"
        second = store.add_feedback(sid, 2, "Follow-up comment", owner_id=ALICE)
        assert store.list_feedback(sid) == (first, second)
        restored = store.load(sid)
        assert restored.state.turns[0] == saved.state.turns[0]
        assert restored.metadata.revision == 2
        # Comments never join the engine's conversation or question inputs.
        assert len(seen) == 1 and "comment" not in repr(seen)
        assert set(json.loads(ordinary_rows(store.path)["sessions"][0][5])) == {"turns", "acquisitions"}
        with closing(sqlite3.connect(store.path)) as connection:
            assert connection.execute("SELECT submission_count FROM user_submissions").fetchone()[0] == 1
    finally:
        release.set()
        manager.shutdown()


def test_feedback_mutations_authorize_owner_before_decoding_private_body(tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = completed(store)
    sid = saved.metadata.session_id
    first = store.add_feedback(sid, 1, "Owner's comment", owner_id=ALICE)
    monkeypatch.setattr(session_store, "_decode", lambda *a: pytest.fail("unauthorized body decoded"))
    for owner in (BOB, "admin@example.test", None, ""):
        with pytest.raises(SessionStoreError, match="session_not_found"):
            store.add_feedback(sid, 1, "Foreign comment", owner_id=owner)
        with pytest.raises(SessionStoreError, match="session_not_found"):
            store.delete_feedback(sid, 1, first.feedback_id, owner_id=owner)


@pytest.mark.parametrize("text", ["", " \t\r\n ", None, 1, ["comment"], "x" * (MAX_ANSWER_FEEDBACK_CHARS + 1),
                                  "nul\x00text", "control\x1f", "delete\x7f", "\ud800"])
def test_feedback_rejects_malformed_and_overlong_plain_text_without_storage_changes(tmp_path, text):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = completed(store)
    before = ordinary_rows(store.path)
    with pytest.raises(SessionStoreError, match="invalid_feedback"):
        store.add_feedback(saved.metadata.session_id, 1, text, owner_id=ALICE)
    assert store.list_feedback(saved.metadata.session_id) == ()
    assert ordinary_rows(store.path) == before


@pytest.mark.parametrize("index", [0, -1, 2, True, "1", None])
def test_feedback_requires_exact_completed_answer_index(tmp_path, index):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = completed(store)
    with pytest.raises(SessionStoreError, match="feedback_turn_not_found"):
        store.add_feedback(saved.metadata.session_id, index, "Comment", owner_id=ALICE)
    assert store.list_feedback(saved.metadata.session_id) == ()


def test_feedback_limit_unicode_and_wrong_comment_association(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved, other = completed(store), completed(store)
    sid = saved.metadata.session_id
    first = store.add_feedback(sid, 1, "é" * MAX_ANSWER_FEEDBACK_CHARS, owner_id=ALICE)
    assert len(first.text) == MAX_ANSWER_FEEDBACK_CHARS
    with pytest.raises(SessionStoreError, match="feedback_not_found"):
        store.delete_feedback(other.metadata.session_id, 1, first.feedback_id, owner_id=ALICE)
    with pytest.raises(SessionStoreError, match="feedback_not_found"):
        store.delete_feedback(sid, 1, "missing", owner_id=ALICE)
    assert store.list_feedback(sid) == (first,)
    store.delete(sid, revision=1)
    with closing(sqlite3.connect(store.path)) as connection:
        assert connection.execute("SELECT count(*) FROM answer_feedback").fetchone()[0] == 0
    assert store.load(other.metadata.session_id) == other


def test_concurrent_feedback_and_clock_adjustment_keep_submission_order(tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    sid = completed(store).metadata.session_id
    with ThreadPoolExecutor(max_workers=4) as pool:
        comments = tuple(pool.map(lambda n: store.add_feedback(sid, 1, str(n), owner_id=ALICE), range(8)))
    assert {f.feedback_id for f in store.list_feedback(sid)} == {f.feedback_id for f in comments}
    prior = store.list_feedback(sid)

    class EarlierClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2020, 1, 1, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(session_store, "datetime", EarlierClock)
    last = store.add_feedback(sid, 1, "Submitted last", owner_id=ALICE)
    assert store.list_feedback(sid) == (*prior, last)


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_historical_sqlite_migration_adds_empty_feedback_without_rewriting_payload(tmp_path, version):
    path = tmp_path / f"schema{version}.sqlite3"
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    stamp, sid = "2020-01-01T00:00:00+00:00", "a" * 32
    with closing(sqlite3.connect(path)) as connection:
        if version < 3:
            connection.execute("CREATE TABLE sessions (session_id TEXT PRIMARY KEY, created_at TEXT, "
                               "updated_at TEXT, title TEXT, revision INTEGER, payload TEXT)")
            values = (sid, stamp, stamp, "Historical", 1, payload)
            connection.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)", values)
            if version == 2:
                connection.execute(session_store._DOCUMENTS_SQL)
        else:
            connection.execute(session_store._SESSIONS_SQL)
            connection.execute(session_store._DOCUMENTS_SQL)
            connection.execute(session_store._IMAGES_SQL)
            jobs_sql = session_store._JOBS_SQL
            if version == 3:
                jobs_sql = jobs_sql.replace(",\n    run_settings TEXT, run_receipt TEXT", "")
            connection.execute(jobs_sql)
            connection.execute("CREATE UNIQUE INDEX one_active_research_job ON research_jobs(session_id) "
                               "WHERE state IN ('queued', 'researching')")
            if version >= 4:
                connection.execute(session_store._PREFERENCES_SQL)
            if version == 5:
                connection.execute("ALTER TABLE sessions ADD COLUMN owner_id TEXT")
                connection.execute("CREATE INDEX sessions_owner ON sessions(owner_id)")
                connection.execute(session_store._SUBMISSIONS_SQL)
                connection.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)",
                                   (sid, stamp, stamp, "Historical", 1, payload, "en", ALICE))
            else:
                connection.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
                                   (sid, stamp, stamp, "Historical", 1, payload, "en"))
        connection.execute(f"PRAGMA user_version={version}")
        connection.commit()
    store = SQLiteSessionStore(path)
    saved = store.load(sid)
    assert saved.state.turns[0].citations and saved.state.turns[0].selected_evidence
    assert store.list_feedback(sid) == ()
    if version == 5:
        assert store.add_feedback(sid, 1, "Historical answer comment", owner_id=ALICE)
    else:
        with pytest.raises(SessionStoreError, match="session_not_found"):
            store.add_feedback(sid, 1, "Cannot claim a local conversation", owner_id=ALICE)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT payload FROM sessions").fetchone()[0] == payload
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SQLiteSessionStore.SCHEMA_VERSION


def test_feedback_database_enforces_text_limit(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    sid = completed(store).metadata.session_id
    with closing(sqlite3.connect(store.path)) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO answer_feedback VALUES (?,?,?,?,?,?)",
                               ("f" * 32, sid, 1, ALICE, "2026-11-04T00:00:00+00:00", "x" * 2001))
