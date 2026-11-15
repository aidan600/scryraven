"""Bounded, best-effort publication for the Reading Room's public activity events."""

import json
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Condition, Thread, current_thread

from scryraven.session_store import MAX_ACTIVITY_BYTES, SQLiteSessionStore

MAX_ACTIVITY_EVENTS = 128
_MAX_LIVE_HISTORIES = 16
_BATCH_DELAY = 0.15
_IDLE_SECONDS = 2
_DISPLAY_FIELDS = frozenset({
    "type", "label", "activity_id", "operations", "elapsed_seconds", "current", "current_since", "current_id", "at",
})


@dataclass
class _RunActivity:
    session_id: str | None
    events: deque[str] = field(default_factory=deque)
    cursor: int = 0
    saved_cursor: int = 0
    byte_count: int = 2  # JSON array brackets. Each entry also reserves one separator byte.
    finished: bool = False

    def append(self, event: dict) -> None:
        entry = {key: value for key, value in event.items() if key in _DISPLAY_FIELDS}
        entry.setdefault("at", datetime.now(timezone.utc).isoformat())
        entry["seq"] = self.cursor + 1
        try:
            encoded = json.dumps(entry, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError, RecursionError):
            return
        size = len(encoded) + 1
        if size + 2 > MAX_ACTIVITY_BYTES:
            return
        while len(self.events) >= MAX_ACTIVITY_EVENTS or self.byte_count + size > MAX_ACTIVITY_BYTES:
            self.byte_count -= len(self.events.popleft()) + 1
        self.cursor += 1
        self.events.append(encoded)
        self.byte_count += size


def _decode(payload: str | None) -> list[dict]:
    if not payload or len(payload) > MAX_ACTIVITY_BYTES:
        return []
    try:
        events = json.loads(payload)
    except (ValueError, RecursionError):
        return []
    if not isinstance(events, list) or len(events) > MAX_ACTIVITY_EVENTS:
        return []
    previous = None
    for event in events:
        if not isinstance(event, dict) or type(event.get("seq")) is not int or event["seq"] < 1:
            return []
        if previous is not None and event["seq"] != previous + 1:
            return []
        previous = event["seq"]
    return events


class ActivityJournal:
    """Publish projected activity immediately and coalesce optional durable writes."""

    def __init__(self, store: SQLiteSessionStore) -> None:
        self._store = store
        self._condition = Condition()
        self._runs: OrderedDict[str, _RunActivity] = OrderedDict()
        self._worker: Thread | None = None
        self._closed = False

    def publisher(self, job_id: str, *, session_id: str | None = None) -> Callable[[dict], None]:
        with self._condition:
            run = self._runs.get(job_id)
            if run is None and not self._closed:
                if len(self._runs) >= _MAX_LIVE_HISTORIES:
                    oldest_finished = next((key for key, value in self._runs.items() if value.finished), None)
                    if oldest_finished is not None:
                        del self._runs[oldest_finished]
                if len(self._runs) < _MAX_LIVE_HISTORIES:
                    run = self._runs[job_id] = _RunActivity(session_id)

        def publish(event: dict) -> None:
            if run is None or not isinstance(event.get("type"), str):
                return
            with self._condition:
                if self._closed or run.finished or self._runs.get(job_id) is not run:
                    return
                run.append(event)
                if run.cursor > run.saved_cursor:
                    self._start_writer()

        return publish

    def finish(self, job_id: str) -> None:
        """Seal activity for a worker that has returned. The job row owns terminal state."""
        with self._condition:
            run = self._runs.get(job_id)
            if run is not None:
                run.finished = True
                if run.cursor > run.saved_cursor:
                    self._start_writer()

    def discard_session(self, session_id: str) -> None:
        with self._condition:
            for job_id in tuple(self._runs):
                if self._runs[job_id].session_id == session_id:
                    del self._runs[job_id]

    def close(self) -> None:
        """Stop publication and give the background writer a bounded final attempt."""
        with self._condition:
            self._closed = True
            self._condition.notify_all()
            worker = self._worker
        if worker is not None and worker is not current_thread():
            worker.join(timeout=1)

    def read(self, session_id: str, job_id: str, *, owner_id: str | None, after: int = 0) -> dict:
        result = self._store.read_job_activity(session_id, job_id, owner_id=owner_id)
        events = _decode(result.pop("events"))
        with self._condition:
            run = self._runs.get(job_id)
            live = tuple(run.events) if run is not None and run.cursor > (events[-1]["seq"] if events else 0) else ()
        if live:
            events = [json.loads(encoded) for encoded in live]
        last_event = events[-1] if events else None
        cursor = last_event["seq"] if last_event else 0
        earliest = events[0]["seq"] if events else 1
        reset = after > cursor or (after != 0 and after < earliest - 1)
        return dict(
            result, events=events if reset else [event for event in events if event["seq"] > after],
            last_event=last_event, cursor=cursor, first_cursor=earliest if events else 0,
            reset=reset, truncated=earliest > 1, available=bool(events),
        )

    def _start_writer(self) -> None:
        if self._closed:
            return
        if self._worker is None:
            self._worker = Thread(target=self._write, name="scryraven-activity-journal", daemon=True)
            try:
                self._worker.start()
            except RuntimeError:
                self._worker = None
        self._condition.notify()

    def _has_pending(self) -> bool:
        return self._closed or any(run.saved_cursor < run.cursor for run in self._runs.values())

    def _write(self) -> None:
        delay = _BATCH_DELAY
        while True:
            with self._condition:
                if not self._condition.wait_for(self._has_pending, timeout=_IDLE_SECONDS):
                    self._worker = None
                    return
                self._condition.wait_for(lambda: self._closed, timeout=delay)
                closing = self._closed
                pending = tuple((job_id, run.cursor, tuple(run.events)) for job_id, run in self._runs.items()
                                if run.saved_cursor < run.cursor)
                if not pending:
                    if closing:
                        self._worker = None
                        return
                    continue
            snapshots = tuple((job_id, cursor, "[" + ",".join(events) + "]")
                              for job_id, cursor, events in pending)
            try:
                self._store.save_job_activity_batch(snapshots)
            except Exception:
                # Failure of an optional journal never changes a job. Retry with backoff.
                delay = min(delay * 2, _IDLE_SECONDS)
            else:
                delay = _BATCH_DELAY
                with self._condition:
                    for job_id, cursor, _ in pending:
                        run = self._runs.get(job_id)
                        if run is not None:
                            run.saved_cursor = cursor
            if closing:
                with self._condition:
                    self._worker = None
                return
