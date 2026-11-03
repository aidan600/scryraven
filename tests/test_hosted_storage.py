"""Synthetic ownership, durable quotas and fair hosted worker admission."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import pytest
from test_persistent_sessions import tmp_path as external_tmp_path
from test_research_jobs import key, result, run_settings

from scryraven import session_store
from scryraven.research_jobs import ResearchJobManager
from scryraven.session_store import SessionStoreError, SQLiteSessionStore

tmp_path = external_tmp_path
ALICE = "alice@example.test"
BOB = "bob@example.test"


def admit(store, question, number, owner=ALICE, quota=10, **kwargs):
    return store.accept_job(question, idempotency_key=key(number), owner_id=owner,
                            submission_quota=quota, **kwargs)


def test_additive_schema_four_migration_preserves_exact_history_and_unowned_sessions(tmp_path):
    path = tmp_path / "schema4.sqlite3"
    payload = (Path(__file__).parent / "fixtures/historical_session_v1.json").read_text(encoding="utf-8")
    stamp, session_id = "2020-01-01T00:00:00+00:00", "a" * 32
    with closing(sqlite3.connect(path)) as connection:
        for sql in (session_store._SESSIONS_SQL, session_store._DOCUMENTS_SQL, session_store._IMAGES_SQL,
                    session_store._JOBS_SQL, session_store._PREFERENCES_SQL):
            connection.execute(sql)
        connection.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?)",
                           (session_id, stamp, stamp, "Legacy", 1, payload, "en"))
        connection.execute("PRAGMA user_version=4")
        connection.commit()
    store = SQLiteSessionStore(path)
    old = store.load(session_id)
    assert old.metadata.owner_id is None
    assert old.state.turns[0].citations and old.state.turns[0].selected_evidence
    assert not store.list_sessions(owner_id=ALICE)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT payload FROM sessions").fetchone()[0] == payload
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
    alice = store.create("Owned", owner_id=ALICE)
    assert store.rename(alice.metadata.session_id, "Renamed").owner_id == ALICE
    assert [s.session_id for s in store.list_sessions(owner_id=ALICE)] == [alice.metadata.session_id]
    assert len(store.list_sessions()) == 2
    assert store.get_metadata(alice.metadata.session_id).owner_id == ALICE
    with pytest.raises(SessionStoreError, match="session_not_found"):
        admit(store, "Cannot claim legacy", 1, session_id=session_id, revision=1)


def test_metadata_authorization_does_not_decode_session_body(tmp_path, monkeypatch):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create("Metadata only", owner_id=ALICE)
    monkeypatch.setattr(session_store, "_decode", lambda *a: pytest.fail("body decoded before authorization"))
    assert store.get_metadata(saved.metadata.session_id) == saved.metadata
    with pytest.raises(SessionStoreError, match="session_not_found"):
        store.get_metadata("missing")


def test_replay_and_manipulated_session_cannot_cross_owner(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    alice = admit(store, "A", 1)
    assert admit(store, "A", 1).job_id == alice.job_id
    with pytest.raises(SessionStoreError, match="session_not_found"):
        admit(store, "A", 1, owner=BOB)
    with pytest.raises(SessionStoreError, match="session_not_found"):
        admit(store, "B", 2, owner=BOB, session_id=alice.session_id)
    assert store.find_submission(key(1), owner_id=ALICE).job_id == alice.job_id
    assert store.find_submission(key(1), owner_id=BOB) is None
    assert len(store.list_sessions()) == len(store.list_jobs()) == 1


def test_quota_is_atomic_persistent_and_survives_session_deletion(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    first = admit(store, "A", 1, quota=1)
    assert admit(store, "A", 1, quota=1).job_id == first.job_id
    store.fail_job(first.job_id)
    store.delete(first.session_id)
    with pytest.raises(SessionStoreError, match="submission_quota_exceeded"):
        admit(SQLiteSessionStore(store.path), "A again", 2, quota=1)
    assert not store.list_sessions()
    assert admit(store, "B", 3, owner=BOB, quota=1)


def test_submission_quota_rolls_at_utc_day_boundary(tmp_path, monkeypatch):
    class Clock(datetime):
        current = datetime(2026, 11, 2, 23, 59, 59, tzinfo=timezone.utc)
        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)
    monkeypatch.setattr(session_store, "datetime", Clock)
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    admit(store, "Yesterday", 1, quota=1)
    with pytest.raises(SessionStoreError, match="submission_quota_exceeded"):
        admit(store, "Still yesterday", 2, quota=1)
    Clock.current = datetime(2026, 11, 3, tzinfo=timezone.utc)
    assert admit(store, "Today", 3, quota=1)


def test_quota_concurrent_admissions_never_overshoot_and_rejections_roll_back(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    def submit(number):
        try:
            return admit(store, str(number), number, quota=2)
        except SessionStoreError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(submit, range(1, 6)))
    assert sum(not isinstance(value, str) for value in results) == 2
    assert results.count("submission_quota_exceeded") == 3
    assert len(store.list_sessions()) == len(store.list_jobs()) == 2


def test_failed_validation_and_queue_rejection_do_not_charge_quota(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    with pytest.raises(SessionStoreError, match="research_queue_full"):
        admit(store, "No room", 1, quota=1, capacity=0)
    with pytest.raises(SessionStoreError, match="invalid_image_selection"):
        admit(store, "Bad image", 2, quota=1, retained_image_ids=("I999",))
    assert not store.list_sessions()
    assert admit(store, "Accepted", 3, quota=1)


def test_two_users_overlap_while_same_owner_queues_and_then_resumes(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    started = {name: Event() for name in "ABC"}
    release = {name: Event() for name in "ABC"}
    seen = {}
    def options(job):
        owner = store.load(job.session_id).metadata.owner_id
        def engine(question, **kwargs):
            seen[question] = owner
            started[question].set()
            assert release[question].wait(10)
            return result(question)
        return {"engine": engine}
    manager = ResearchJobManager(store, session_options_factory=options)
    try:
        a = manager.submit("A", idempotency_key=key(1), owner_id=ALICE, submission_quota=10)
        assert started["A"].wait(5)
        b = manager.submit("B", idempotency_key=key(2), owner_id=ALICE, submission_quota=10)
        c = manager.submit("C", idempotency_key=key(3), owner_id=BOB, submission_quota=10)
        assert started["C"].wait(5)
        assert manager.get(b.job_id).state == "queued" and not started["B"].is_set()
        assert manager.get(a.job_id).state == manager.get(c.job_id).state == "researching"
        release["A"].set()
        assert started["B"].wait(5)
    finally:
        for event in release.values():
            event.set()
        assert manager.wait_idle(10)
        manager.shutdown()
    assert seen == {"A": ALICE, "C": BOB, "B": ALICE}
    for job in (a, b, c):
        saved = store.load(job.session_id)
        assert saved.state.turns[0].question == job.question
        assert saved.metadata.owner_id == seen[job.question]


def test_one_active_owner_cannot_grow_waiting_queue_past_eight(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    started, release = Event(), Event()
    def blocked(question, **kwargs):
        started.set()
        assert release.wait(10)
        return result(question)
    manager = ResearchJobManager(store, session_options={"engine": blocked})
    try:
        manager.submit("active", idempotency_key=key(1), owner_id=ALICE, submission_quota=20)
        assert started.wait(5)
        for number in range(2, 10):
            manager.submit(str(number), idempotency_key=key(number), owner_id=ALICE, submission_quota=20)
        with pytest.raises(SessionStoreError, match="research_queue_full"):
            manager.submit("overflow", idempotency_key=key(10), owner_id=BOB, submission_quota=20)
        assert sum(job.state == "queued" for job in manager.list()) == 8
    finally:
        release.set()
        assert manager.wait_idle(10)
        manager.shutdown()


def test_owner_retry_charges_quota_keeps_snapshot_and_restart_does_not_dispatch(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    first = admit(store, "A", 1, quota=1, run_settings=run_settings())
    calls = []
    manager = ResearchJobManager(store, session_options={"engine": lambda *a, **k: calls.append(a)})
    assert manager.get(first.job_id).state == "interrupted" and not calls
    with pytest.raises(SessionStoreError, match="session_not_found"):
        manager.retry(first.job_id, idempotency_key=key(2), owner_id=BOB, submission_quota=2)
    with pytest.raises(SessionStoreError, match="submission_quota_exceeded"):
        manager.retry(first.job_id, idempotency_key=key(2), owner_id=ALICE, submission_quota=1)
    manager.options["engine"] = lambda question, **kwargs: result(question)
    second = manager.retry(first.job_id, idempotency_key=key(2), owner_id=ALICE, submission_quota=2)
    assert manager.wait_idle()
    manager.shutdown()
    assert second.run_settings == first.run_settings
    assert store.load(first.session_id).metadata.owner_id == ALICE
    assert len(store.load(first.session_id).state.turns) == 1
