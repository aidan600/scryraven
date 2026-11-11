"""Durable jobs exercise ordinary ask/commit using controlled worker events."""

import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from threading import Event, Lock

import pytest
from pdf_fixtures import text_pdf
from PIL import Image
from test_persistent_sessions import tmp_path as external_tmp_path

from scryraven.documents import prepare_pdf
from scryraven.images import prepare_image
from scryraven.research_jobs import ResearchJobManager
from scryraven.results import CompletedAnswer
from scryraven.run_settings import RunSettings
from scryraven.session import ResearchSession
from scryraven.session_store import SessionConflictError, SessionStoreError, SQLiteSessionStore

tmp_path = external_tmp_path


def result(question):
    return CompletedAnswer("A conditional result for " + question, "supported", "supported", (), (), (), (), ())


def engine(question, **kwargs):
    return result(question)


def key(number):
    return f"submission-key-{number:08d}"


def run_settings():
    return RunSettings("chatgpt_plan", "gpt-6.1-terra", "medium", "gpt-6.1-sol", "medium", None, 40)


def set_legacy_job_schema(store, version):
    with closing(sqlite3.connect(store.path)) as connection:
        connection.execute("ALTER TABLE research_jobs DROP COLUMN viewed")
        if version < 6:
            connection.execute("DROP TABLE answer_feedback")
        if version < 5:
            connection.execute("DROP INDEX sessions_owner")
            connection.execute("ALTER TABLE sessions DROP COLUMN owner_id")
            connection.execute("DROP TABLE user_submissions")
        if version < 4:
            connection.execute("ALTER TABLE research_jobs DROP COLUMN run_settings")
            connection.execute("ALTER TABLE research_jobs DROP COLUMN run_receipt")
            connection.execute("DROP TABLE app_preferences")
        connection.execute(f"PRAGMA user_version={version}")
        connection.commit()


@pytest.mark.parametrize("version", [3, 4, 5, 6])
def test_migration_marks_only_preexisting_completed_jobs_viewed(tmp_path, version):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    owner = "owner@example.test" if version >= 5 else None
    document = prepare_pdf("notes.pdf", "application/pdf", text_pdf(["Historical notes"]))
    manager = ResearchJobManager(store, session_options={"engine": engine})
    try:
        first = manager.submit("A previous answer", idempotency_key=key(1), owner_id=owner, documents=(document,))
        assert manager.wait_idle()
        manager.submit("Another historical answer", idempotency_key=key(2), owner_id=owner,
                       session_id=first.session_id, revision=1)
        assert manager.wait_idle()
    finally:
        manager.shutdown()

    store.accept_job("An interrupted job", idempotency_key=key(3))
    store.interrupt_jobs()
    failed = store.accept_job("A failed job", idempotency_key=key(4))
    store.fail_job(failed.job_id)
    store.accept_job("A researching job", idempotency_key=key(5))
    store.claim_next_job()
    store.accept_job("A queued job", idempotency_key=key(6))
    if version == 6:
        store.add_feedback(first.session_id, 1, "Historical feedback", owner_id=owner)

    jobs = store.list_jobs()
    assert sorted(job.state for job in jobs) == ["completed", "completed", "failed", "interrupted", "queued", "researching"]
    assert all(not job.viewed for job in jobs)
    session = store.load(first.session_id)
    feedback = store.list_feedback(first.session_id)
    set_legacy_job_schema(store, version)

    reopened = SQLiteSessionStore(store.path)
    assert reopened.list_jobs() == tuple(replace(job, viewed=job.state == "completed") for job in jobs)
    assert reopened.load(first.session_id) == session
    assert reopened.list_feedback(first.session_id) == feedback


@pytest.mark.parametrize("migrated", [False, True], ids=["fresh", "migrated"])
def test_new_completion_starts_unread_and_view_does_not_change_session(tmp_path, migrated):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    if migrated:
        assert store.list_jobs() == ()
        set_legacy_job_schema(store, 6)
    owner = "owner@example.test"
    manager = ResearchJobManager(store, session_options={"engine": engine})
    try:
        job = manager.submit("A new answer", idempotency_key=key(1), owner_id=owner)
        assert manager.wait_idle()
        assert manager.get(job.job_id).state == "completed"
        assert not manager.get(job.job_id).viewed
        original_session = store.load(job.session_id)
        with pytest.raises(SessionStoreError, match="job_not_found"):
            store.acknowledge_completion(job.session_id, job.job_id, owner_id="another@example.test")
        store.acknowledge_completion(job.session_id, job.job_id, owner_id=owner)
        assert store.load(job.session_id) == original_session
        followup = manager.submit("A later answer", idempotency_key=key(2), owner_id=owner,
                                  session_id=job.session_id, revision=1)
        assert manager.wait_idle()
    finally:
        manager.shutdown()

    reopened = SQLiteSessionStore(store.path)
    assert reopened.get_job(job.job_id).viewed
    assert reopened.get_job(followup.job_id).state == "completed"
    assert not reopened.get_job(followup.job_id).viewed
    pending = reopened.accept_job("A future answer", session_id=job.session_id, revision=2,
                                  idempotency_key=key(3), owner_id=owner)
    with pytest.raises(SessionStoreError, match="job_not_found"):
        reopened.acknowledge_completion(job.session_id, pending.job_id, owner_id=owner)
    assert not reopened.get_job(pending.job_id).viewed


class Workers:
    def __init__(self):
        self.started = {name: Event() for name in ("A", "B", "C")}
        self.release = {name: Event() for name in ("A", "B", "C")}
        self.calls = []
        self.lock = Lock()
        self.active = self.maximum = 0

    def __call__(self, question, **kwargs):
        with self.lock:
            self.calls.append(question)
            self.active += 1
            self.maximum = max(self.maximum, self.active)
        self.started[question].set()
        assert self.release[question].wait(10)
        with self.lock:
            self.active -= 1
        return result(question)

    def finish(self):
        for release in self.release.values():
            release.set()


def test_two_independent_workers_and_bounded_queue_keep_exactly_one_commit(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    workers = Workers()
    manager = ResearchJobManager(store, session_options={"engine": workers})
    try:
        a = manager.submit("A", idempotency_key=key(1))
        b = manager.submit("B", idempotency_key=key(2))
        assert workers.started["A"].wait(5) and workers.started["B"].wait(5)
        c = manager.submit("C", idempotency_key=key(3))
        assert manager.get(c.job_id).state == "queued"
        assert store.load(a.session_id).state.turns == ()
        assert store.load(b.session_id).state.turns == ()
        duplicate = manager.submit("A", idempotency_key=key(1))
        assert duplicate.job_id == a.job_id
        with pytest.raises(SessionStoreError, match="session_busy"):
            manager.submit("another", session_id=a.session_id, revision=0, idempotency_key=key(4))
        # An unrelated read, rename and a second session all work while A waits.
        store.rename(a.session_id, "Renamed while researching")
        with pytest.raises(SessionStoreError, match="session_busy"):
            store.delete(a.session_id)
        with pytest.raises(SessionStoreError, match="session_busy"):
            store.attach_document(a.session_id, 0, "notes.pdf", "application/pdf", text_pdf(["notes"]))
        workers.release["A"].set()
        assert workers.started["C"].wait(5)
        assert manager.get(a.job_id).state == "completed"
        assert manager.get(b.job_id).state == "researching"
        assert store.load(a.session_id).metadata.title == "Renamed while researching"
    finally:
        workers.finish()
        assert manager.wait_idle(10)
        manager.shutdown()
    assert workers.maximum == 2
    assert sorted(workers.calls) == ["A", "B", "C"]
    assert all(job.state == "completed" for job in manager.list())
    for job in (a, b, c):
        saved = store.load(job.session_id)
        assert saved.metadata.revision == 1
        assert [turn.question for turn in saved.state.turns] == [job.question]
    with pytest.raises(SessionStoreError, match="research_server_stopping"):
        manager.submit("D", idempotency_key=key(8))


def test_admission_queue_is_durable_bounded_and_idempotent(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    first = store.accept_job("A", idempotency_key=key(1))
    for number in range(2, 11):
        store.accept_job(str(number), idempotency_key=key(number))
    with pytest.raises(SessionStoreError, match="research_queue_full"):
        store.accept_job("overflow", idempotency_key=key(11))
    assert store.accept_job("A", idempotency_key=key(1)).job_id == first.job_id
    with pytest.raises(SessionStoreError, match="submission_conflict"):
        store.accept_job("different question", idempotency_key=key(1))
    assert len(store.list_sessions()) == len(store.list_jobs()) == 10


def test_failed_question_survives_and_explicit_retry_is_independent(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    def broken(question, **kwargs):
        raise RuntimeError("private transport body must never become public status")
    manager = ResearchJobManager(store, session_options={"engine": broken})
    first = manager.submit("Keep my question", idempotency_key=key(1), run_settings=run_settings())
    assert manager.wait_idle()
    failed = manager.get(first.job_id)
    assert failed.question == "Keep my question" and failed.state == "failed"
    assert failed.error_code == "research_failed" and store.load(first.session_id).metadata.revision == 0
    manager.options["engine"] = engine
    second = manager.retry(first.job_id, idempotency_key=key(2))
    assert manager.wait_idle()
    assert manager.get(second.job_id).state == "completed"
    assert manager.get(first.job_id).state == "failed"
    assert len(store.load(first.session_id).state.turns) == 1
    with pytest.raises(SessionStoreError, match="job_not_retryable"):
        manager.retry(second.job_id, idempotency_key=key(3))
    with pytest.raises(SessionConflictError):
        manager.retry(first.job_id, idempotency_key=key(4))
    manager.shutdown()


def test_shutdown_prevents_late_commit_and_restart_never_reexecutes(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    workers = Workers()
    manager = ResearchJobManager(store, session_options={"engine": workers})
    a = manager.submit("A", idempotency_key=key(1))
    assert workers.started["A"].wait(5)
    manager.shutdown()
    assert manager.get(a.job_id).state == "interrupted"
    with pytest.raises(SessionStoreError, match="research_server_owned"):
        ResearchJobManager(SQLiteSessionStore(store.path))
    workers.finish()
    assert manager.wait_idle()
    assert store.load(a.session_id).state.turns == ()
    calls = []
    restarted = ResearchJobManager(SQLiteSessionStore(store.path), session_options={"engine": lambda *a, **k: calls.append(a)})
    assert restarted.get(a.job_id).state == "interrupted"
    assert restarted.wait_idle() and calls == []
    restarted.shutdown()


def test_startup_marks_queued_and_running_jobs_interrupted_without_worker_calls(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    first = store.accept_job("A", idempotency_key=key(1))
    store.claim_next_job()
    second = store.accept_job("B", idempotency_key=key(2))
    manager = ResearchJobManager(store, session_options={"engine": lambda *a, **k: pytest.fail("must not restart")})
    assert manager.get(first.job_id).state == manager.get(second.job_id).state == "interrupted"
    assert manager.wait_idle()
    manager.shutdown()


def test_second_manager_cannot_interrupt_the_live_database_owner(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    workers = Workers()
    manager = ResearchJobManager(store, session_options={"engine": workers})
    try:
        job = manager.submit("A", idempotency_key=key(1))
        assert workers.started["A"].wait(5)
        with pytest.raises(SessionStoreError, match="research_server_owned"):
            ResearchJobManager(SQLiteSessionStore(store.path))
        assert manager.get(job.job_id).state == "researching"
        script = """
import sys
from scryraven.research_jobs import ResearchJobManager
from scryraven.session_store import SQLiteSessionStore, SessionStoreError
try:
    manager = ResearchJobManager(SQLiteSessionStore(sys.argv[1]))
except SessionStoreError as error:
    print(error.code)
else:
    manager.shutdown()
    raise SystemExit('unexpected second owner')
"""
        attempted = subprocess.run([sys.executable, "-c", script, str(store.path)],
                                   cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=15)
        assert attempted.returncode == 0 and attempted.stdout.strip() == "research_server_owned"
        assert attempted.stderr == "" and manager.get(job.job_id).state == "researching"
        workers.finish()
        assert manager.wait_idle()
        assert manager.get(job.job_id).state == "completed" and store.load(job.session_id).metadata.revision == 1
    finally:
        workers.finish()
        manager.wait_idle()
        manager.shutdown()


def test_database_ownership_recovers_after_process_exit_without_stale_lock(tmp_path):
    path = tmp_path / "sessions.sqlite3"
    script = """
import os
import sys
from scryraven.research_jobs import ResearchJobManager
from scryraven.session_store import SQLiteSessionStore
store = SQLiteSessionStore(sys.argv[1])
manager = ResearchJobManager(store)
job = store.accept_job('Accepted before process exit', idempotency_key='subprocess-exit-key')
print(job.job_id, flush=True)
sys.stdin.readline()
os._exit(0)
"""
    process = subprocess.Popen([sys.executable, "-c", script, str(path)],
                               cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        job_id = process.stdout.readline().strip()
        assert len(job_id) == 32
        with pytest.raises(SessionStoreError, match="research_server_owned"):
            ResearchJobManager(SQLiteSessionStore(path))
        assert SQLiteSessionStore(path).get_job(job_id).state == "queued"
        process.communicate("exit\n", timeout=15)
        assert process.returncode == 0
        manager = ResearchJobManager(SQLiteSessionStore(path))
        try:
            assert manager.get(job_id).state == "interrupted" and manager.wait_idle()
            assert path.with_name(path.name + ".reading-room.lock").exists()
        finally:
            manager.shutdown()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=15)


def test_intervening_completed_turn_is_never_overwritten(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    original = ResearchSession.create(store=store, engine=engine)
    original.ask("Older turn")
    older = original.turns
    workers = Workers()
    manager = ResearchJobManager(store, session_options={"engine": workers})
    a = manager.submit("A", session_id=original.session_id, revision=1, idempotency_key=key(1))
    assert workers.started["A"].wait(5)
    intervening = ResearchSession.open(original.session_id, store=store, engine=engine)
    intervening.ask("Intervening committed turn")
    workers.finish()
    assert manager.wait_idle()
    assert manager.get(a.job_id).state == "failed"
    assert manager.get(a.job_id).error_code == "session_conflict"
    saved = store.load(original.session_id)
    assert saved.state.turns[:1] == older
    assert [t.question for t in saved.state.turns] == ["Older turn", "Intervening committed turn"]
    with pytest.raises(SessionConflictError):
        manager.submit("stale", session_id=original.session_id, revision=1, idempotency_key=key(2))
    manager.shutdown()


def test_turn_and_job_completion_roll_back_together(tmp_path):
    class BrokenCommit(SQLiteSessionStore):
        def _commit(self, connection, session_id, revision, state):
            super()._commit(connection, session_id, revision, state)
            raise SessionStoreError()
    store = BrokenCommit(tmp_path / "sessions.sqlite3")
    manager = ResearchJobManager(store, session_options={"engine": engine})
    job = manager.submit("A", idempotency_key=key(1))
    assert manager.wait_idle()
    assert manager.get(job.job_id).state == "failed"
    assert store.load(job.session_id).state.turns == ()
    assert store.load(job.session_id).metadata.revision == 0
    manager.shutdown()


@pytest.mark.parametrize("failure", ["claim", "fail"])
def test_storage_failure_never_strands_queued_questions_or_replays_calls(tmp_path, capsys, failure):
    class UnavailableStore(SQLiteSessionStore):
        unavailable = False
        def claim_next_job(self):
            if self.unavailable and failure == "claim":
                raise SessionStoreError()
            return super().claim_next_job()
        def fail_job(self, *args, **kwargs):
            if self.unavailable:
                raise SessionStoreError()
            return super().fail_job(*args, **kwargs)
        def interrupt_jobs(self, *args, **kwargs):
            if self.unavailable:
                raise SessionStoreError()
            return super().interrupt_jobs(*args, **kwargs)
    store = UnavailableStore(tmp_path / "sessions.sqlite3")
    calls = []
    def broken(question, **kwargs):
        calls.append(question)
        raise RuntimeError("PRIVATE_MODEL_ERROR")
    manager = ResearchJobManager(store, session_options={"engine": broken})
    store.unavailable = True
    job = manager.submit("Keep this accepted question", idempotency_key=key(1), run_settings=run_settings())
    assert manager.wait_idle()
    with pytest.raises(SessionStoreError):
        manager.list()
    store.unavailable = False
    recovered = manager.get(job.job_id)
    assert recovered.state == "interrupted" and recovered.error_code == "storage_interrupted"
    assert recovered.question == "Keep this accepted question"
    assert calls == ([] if failure == "claim" else ["Keep this accepted question"])
    assert store.load(job.session_id).metadata.revision == 0
    assert capsys.readouterr().err == ""
    manager.options["engine"] = engine
    retried = manager.retry(job.job_id, idempotency_key=key(2))
    assert manager.wait_idle() and manager.get(retried.job_id).state == "completed"
    manager.shutdown()


def test_language_preference_persists_and_jobs_keep_the_accepted_language(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    saved = store.create()
    assert saved.metadata.citation_language == "en"
    store.set_citation_language(saved.metadata.session_id, "pl")
    assert SQLiteSessionStore(store.path).load(saved.metadata.session_id).metadata.citation_language == "pl"
    seen = []
    def inspect(question, **kwargs):
        seen.append(kwargs["context"]["citation_description_language"])
        return result(question)
    manager = ResearchJobManager(store, session_options={"engine": inspect})
    job = manager.submit("A", session_id=saved.metadata.session_id, idempotency_key=key(1), citation_language="en")
    store.set_citation_language(saved.metadata.session_id, "fr")
    assert manager.wait_idle()
    assert manager.get(job.job_id).citation_language == "en" and seen == ["en"]
    assert store.load(saved.metadata.session_id).metadata.citation_language == "fr"
    with pytest.raises(SessionStoreError, match="invalid_citation_language"):
        store.set_citation_language(saved.metadata.session_id, "invented")
    manager.shutdown()


def test_attachments_are_owned_and_admitted_with_question_atomically(tmp_path):
    store = SQLiteSessionStore(tmp_path / "sessions.sqlite3")
    png = BytesIO()
    Image.new("RGB", (64, 64), "red").save(png, format="PNG")
    image = prepare_image("../../picture.png", "image/png", png.getvalue())
    document = prepare_pdf("notes.pdf", "application/pdf", text_pdf(["Public notes"]))
    job = store.accept_job("Read these", idempotency_key=key(1), images=(image,), documents=(document,))
    saved = store.load(job.session_id)
    assert job.image_ids == ("I1",) and job.document_ids == ("D1",)
    assert saved.images[0].original_image == png.getvalue()
    assert saved.images[0].filename == "picture.png" and saved.documents[0].original_pdf == document.original_pdf
    assert SQLiteSessionStore(store.path).load(job.session_id) == saved
    with pytest.raises(SessionStoreError, match="invalid_image_selection"):
        store.accept_job("Cross session image", idempotency_key=key(2), retained_image_ids=("I1",))
    assert len(store.list_sessions()) == len(store.list_jobs()) == 1
    store.interrupt_jobs()
    second = store.accept_job("Reuse retained image", session_id=job.session_id, idempotency_key=key(3),
                              images=(image,), retained_image_ids=("I1",))
    assert second.image_ids == ("I1",) and len(store.load(job.session_id).images) == 1
    store.interrupt_jobs()
    store.delete(job.session_id)
    assert store.list_jobs() == store.list_sessions() == ()
