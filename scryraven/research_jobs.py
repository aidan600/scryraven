"""Bounded local execution of ordinary research sessions, independent of HTTP."""

from __future__ import annotations

import sys
from collections.abc import Callable
from threading import Condition, Thread
from time import monotonic

from scryraven.documents import PreparedDocument
from scryraven.session import ResearchSession
from scryraven.session_store import ResearchJob, SessionConflictError, SessionStoreError, SQLiteSessionStore


class _DatabaseOwner:
    """OS custody of one local runner lifetime; process exit releases the lock.

    The sidecar may remain on disk. Its existence is never an ownership claim;
    only the live OS lock prevents another server from interrupting this owner.
    """

    def __init__(self, store: SQLiteSessionStore):
        self.handle = None
        try:
            store.path.parent.mkdir(parents=True, exist_ok=True)
            handle = store.path.with_name(store.path.name + ".reading-room.lock").open("a+b")
            self.handle = handle
            if handle.seek(0, 2) == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
        except OSError:
            self.close()
            raise SessionStoreError() from None
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.close()
            raise SessionStoreError("research_server_owned") from None

    def close(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def __del__(self):
        self.close()


class _JobStore:
    """Keep the ordinary ask() commit boundary, adding atomic job completion."""

    def __init__(self, store: SQLiteSessionStore, job: ResearchJob, manager):
        self.store, self.job, self.manager = store, job, manager

    def __getattr__(self, name):
        return getattr(self.store, name)

    def commit(self, session_id, revision, state):
        with self.manager.condition:
            if self.manager.closed:
                raise SessionConflictError()
            return self.store.commit_job(self.job.job_id, session_id, revision, state)


class ResearchJobManager:
    """Two local workers and eight waiting admissions; never a research scheduler.

    Only accepted jobs from this server lifetime are dispatched. Restarting marks
    prior work interrupted, requiring an explicit new user submission. Workers
    hold neither an HTTP request nor a SQLite connection during ask().
    """

    concurrency = 2
    queue_capacity = 8

    def __init__(self, store: SQLiteSessionStore, *, session_options: dict | None = None,
                 session_options_factory: Callable[[ResearchJob], dict] | None = None,
                 on_finished: Callable | None = None):
        self.store = store
        self.options = dict(session_options or {})
        self.options_factory = session_options_factory
        self.on_finished = on_finished
        self.condition = Condition()
        self.workers: set[Thread] = set()
        self.closed = False
        self.storage_failed = False
        self.owner = _DatabaseOwner(store)
        try:
            self.store.interrupt_jobs()
        except Exception:
            self.owner.close()
            raise

    def _recover_storage(self):
        # If storage failed after admission, never leave an apparently queued
        # question with no worker. When storage becomes available, mark the
        # interrupted lifetime before reporting status or accepting more work.
        with self.condition:
            if self.storage_failed and not self.closed:
                self.store.interrupt_jobs("storage_interrupted")
                self.storage_failed = False

    def _worker_finished(self, worker: Thread):
        with self.condition:
            self.workers.discard(worker)
            if self.closed and not self.workers:
                self.owner.close()
            self.condition.notify_all()

    def submit(self, question: str, **kwargs) -> ResearchJob:
        with self.condition:
            if self.closed:
                raise SessionStoreError("research_server_stopping")
            self._recover_storage()
            job = self.store.accept_job(question, capacity=self.concurrency + self.queue_capacity, **kwargs)
            if job.state == "queued":
                while len(self.workers) < self.concurrency:
                    worker = Thread(target=self._work, name="scryraven-research", daemon=True)
                    self.workers.add(worker)
                    worker.start()
            return job

    def get(self, job_id: str) -> ResearchJob:
        self._recover_storage()
        return self.store.get_job(job_id)

    def list(self, session_id: str | None = None) -> tuple[ResearchJob, ...]:
        self._recover_storage()
        return self.store.list_jobs(session_id)

    def retry(self, job_id: str, *, idempotency_key: str) -> ResearchJob:
        """Only an explicit user action retries; keep exact question and files."""
        old = self.get(job_id)
        if old.state not in {"failed", "interrupted"}:
            raise SessionStoreError("job_not_retryable")
        saved = self.store.load(old.session_id)
        documents = tuple(PreparedDocument(**{name: getattr(document, name)
                                              for name in PreparedDocument.__dataclass_fields__})
                          for document in saved.documents if document.document_id in old.document_ids)
        return self.submit(old.question, session_id=old.session_id, revision=old.revision,
                           idempotency_key=idempotency_key, documents=documents,
                           retained_image_ids=old.image_ids, citation_language=old.citation_language)

    def _work(self):
        from threading import current_thread

        try:
            while True:
                with self.condition:
                    if self.closed:
                        self._worker_finished(current_thread())
                        return
                    self._recover_storage()
                    job = self.store.claim_next_job()
                    if job is None:
                        self._worker_finished(current_thread())
                        return
                result = error = session = None
                try:
                    options = dict(self.options)
                    if self.options_factory is not None:
                        options.update(self.options_factory(job))
                    session = ResearchSession.open(job.session_id, store=_JobStore(self.store, job, self), **options)
                    if session.metadata.revision != job.revision:
                        raise SessionConflictError()
                    result = session.ask(job.question, image_ids=job.image_ids,
                                         citation_language=job.citation_language)
                except Exception as exc:
                    error = exc
                    code = "session_conflict" if isinstance(exc, SessionConflictError) else getattr(exc, "code", "research_failed")
                    self.store.fail_job(job.job_id, code)
                finally:
                    if self.on_finished is not None:
                        try:
                            self.on_finished(self.store.get_job(job.job_id), result, error, session)
                        except Exception:
                            # Optional diagnostics cannot change the accepted
                            # question, atomic result or public lifecycle.
                            pass
                    with self.condition:
                        self.condition.notify_all()
        except SessionStoreError:
            # No raw exception/transport body is printed by a worker. Recovery
            # performs no inference and never requeues an accepted paid call.
            with self.condition:
                self.storage_failed = True
                try:
                    self._recover_storage()
                except SessionStoreError:
                    pass
        finally:
            self._worker_finished(current_thread())

    def wait_idle(self, timeout: float = 10) -> bool:
        """A condition-based test/operator join, without polling or arbitrary sleeps."""
        deadline = monotonic() + timeout
        with self.condition:
            while self.workers:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return False
                self.condition.wait(remaining)
            return True

    def shutdown(self) -> None:
        """Reject admission/commits immediately; process exit ends daemon workers."""
        with self.condition:
            if self.closed:
                return
            self.closed = True
            try:
                self.store.interrupt_jobs()
            finally:
                # An embedding may keep the process alive after server shutdown.
                # Keep ownership until its in-flight workers actually leave so
                # a replacement server cannot overlap another pair of calls.
                if not self.workers:
                    self.owner.close()
                self.condition.notify_all()
