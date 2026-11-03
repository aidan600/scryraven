"""Protected, bounded hosted copies of the existing diagnostic observer stream.

This directory is operational custody only. Cleanup never touches the session
store, attachments, acquired Evidence, or historical citation snapshots.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread, current_thread
from time import time
from uuid import uuid4

_ID = re.compile(r"[0-9a-f]{32}")
_FILE = re.compile(r"([0-9a-f]{32})\.([0-9a-f]{32})\.(forensic\.jsonl|diagnostic\.json)")


class HostedDiagnostics:
    """One private directory, finite file sizes and finite age/total retention.

Only internally named, regular, single-link files are managed. Active jobs are
not evicted to make room; a full active budget stops recording until space is
available. Source-bearing and body-free records stay separate from app logs.
"""

    def __init__(self, directory: str | Path, *, retention_days: int = 30,
                 max_bytes: int = 512 * 1024 * 1024,
                 max_file_bytes: int = 64 * 1024 * 1024, clock=time):
        if (type(retention_days) is not int or retention_days < 1
                or type(max_bytes) is not int or max_bytes < 1
                or type(max_file_bytes) is not int or max_file_bytes < 1):
            raise ValueError("invalid_diagnostic_retention")
        try:
            chosen = Path(directory).expanduser()
            if chosen.is_symlink():
                raise OSError()
            self.directory = chosen.resolve()
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.directory.chmod(0o700)
            probe = self.directory / (".write-check-" + uuid4().hex)
            descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(descriptor)
            probe.unlink()
        except (OSError, ValueError, RuntimeError):
            raise OSError("hosted_diagnostics_unavailable") from None
        self.retention_days = retention_days
        self.max_bytes = max_bytes
        self.max_file_bytes = min(max_file_bytes, max_bytes)
        self.clock = clock
        self.run_id = uuid4().hex
        self._lock = Lock()
        self._active: set[str] = set()
        self._sequence: dict[str, int] = {}
        self._stopped: dict[str, str] = {}
        self._enabled = True
        self._maintenance_stop = Event()
        self._maintenance_thread = None
        self._maintenance_lifecycle_lock = Lock()
        self._maintenance_closed = False
        self.maintenance()

    def start_maintenance(self, interval_seconds=3600):
        """Production-only idle retention; no application or inference work.

        A daemon wakes hourly by default, bounding idle age overshoot to about
        one interval. Embeddings and tests explicitly opt in; construction alone
        never creates a background thread. Repeated starts share one lifetime.
        """
        if (type(interval_seconds) not in {int, float} or not math.isfinite(interval_seconds)
                or interval_seconds <= 0):
            raise ValueError("invalid_diagnostic_maintenance_interval")
        with self._maintenance_lifecycle_lock:
            if self._maintenance_closed:
                return False
            if self._maintenance_thread is not None:
                return self._maintenance_thread.is_alive()

            def maintain():
                while not self._maintenance_stop.wait(interval_seconds):
                    try:
                        self.maintenance()
                    except Exception:
                        # Operational cleanup cannot propagate into serving or
                        # become an unhandled thread traceback containing paths.
                        with self._lock:
                            self._enabled = False

            thread = Thread(target=maintain, name="scryraven-diagnostic-retention", daemon=True)
            try:
                thread.start()
            except RuntimeError:
                self._enabled = False
                return False
            self._maintenance_thread = thread
            return True

    def close(self):
        """Idempotently stop idle cleanup; an in-progress scan may finish safely."""
        with self._maintenance_lifecycle_lock:
            self._maintenance_closed = True
            self._maintenance_stop.set()
            thread = self._maintenance_thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout=5)

    @staticmethod
    def _identifiers(job):
        if not (_ID.fullmatch(job.session_id) and _ID.fullmatch(job.job_id)):
            raise ValueError("invalid_diagnostic_identity")
        return job.session_id, job.job_id

    @staticmethod
    def _require_owner(owner_id):
        if not isinstance(owner_id, str) or not owner_id.strip() or len(owner_id) > 320:
            raise ValueError("invalid_diagnostic_identity")

    def _path(self, job, suffix):
        session_id, job_id = self._identifiers(job)
        return self.directory / f"{session_id}.{job_id}.{suffix}"

    def _scan(self):
        managed, unmanaged_bytes, unmanaged_files = [], 0, 0
        for path in self.directory.iterdir():
            info = path.lstat()
            match = _FILE.fullmatch(path.name)
            if (match and stat.S_ISREG(info.st_mode) and info.st_nlink == 1):
                managed.append((path, info.st_size, info.st_mtime, match.group(2)))
            else:
                # Never follow, read, modify or delete unknown files or links.
                unmanaged_files += 1
                unmanaged_bytes += info.st_size
        return managed, unmanaged_bytes, unmanaged_files

    def _prune(self, extra=0):
        files, unmanaged_bytes, _ = self._scan()
        threshold = self.clock() - self.retention_days * 86400
        expired = {job_id for _, _, modified, job_id in files
                   if modified < threshold and job_id not in self._active}
        for path, _, _, job_id in files:
            if job_id in expired:
                path.unlink()
        files = [item for item in files if item[3] not in expired]
        total = sum(item[1] for item in files) + unmanaged_bytes
        groups = {}
        for item in files:
            groups.setdefault(item[3], []).append(item)
        for job_id in sorted(groups, key=lambda key: max(item[2] for item in groups[key])):
            if total + extra <= self.max_bytes:
                break
            if job_id in self._active:
                continue
            for path, size, _, _ in groups[job_id]:
                path.unlink()
                total -= size
        return total + extra <= self.max_bytes

    def maintenance(self):
        """Safe to call on requests/health checks, including otherwise idle days."""
        with self._lock:
            try:
                self._prune()
            except OSError:
                self._enabled = False

    @staticmethod
    def _encoded(record):
        return (json.dumps(record, ensure_ascii=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")

    @staticmethod
    def _open(path, flags):
        descriptor = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or path.is_symlink():
            os.close(descriptor)
            raise OSError("unsafe_diagnostic_file")
        return descriptor, info

    def _append(self, path, line, *, file_limit):
        old_size = path.lstat().st_size if path.exists() else 0
        if old_size + len(line) > file_limit:
            return "file_limit"
        if not self._prune(len(line)):
            return "storage_limit"
        descriptor, info = self._open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        with os.fdopen(descriptor, "ab") as target:
            if info.st_size + len(line) > file_limit:
                return "file_limit"
            target.write(line)
        # Test clocks also determine retention; filesystem timestamps remain real.
        if os.utime in os.supports_follow_symlinks:
            os.utime(path, (self.clock(), self.clock()), follow_symlinks=False)
        elif not path.is_symlink():
            os.utime(path, (self.clock(), self.clock()))
        return None

    def observe(self, event: dict, *, job, owner_id: str):
        """Receive only the existing normalized observer, never transport payloads."""
        with self._lock:
            try:
                self._identifiers(job)
                self._require_owner(owner_id)
                self._active.add(job.job_id)
                if not self._enabled or job.job_id in self._stopped:
                    return
                sequence = self._sequence.get(job.job_id, 0) + 1
                record = {
                    "schema_version": 1, "run_id": self.run_id,
                    "event_sequence": sequence,
                    "logged_at_utc": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                    "session_id": job.session_id, "job_id": job.job_id, "owner_id": owner_id,
                    "attempted_turn": job.revision + 1, "revision_before": job.revision,
                    "event": event,
                }
                stopped = self._append(self._path(job, "forensic.jsonl"), self._encoded(record),
                                       file_limit=self.max_file_bytes)
                if stopped:
                    self._stopped[job.job_id] = stopped
                else:
                    self._sequence[job.job_id] = sequence
            except Exception:
                # Diagnostic storage never changes the accepted research result.
                self._stopped[job.job_id] = "write_failed"

    def finish(self, record: dict | None = None, *, job, owner_id: str):
        """Persist a TurnDiagnostics.record projection and close active custody.

        Passing None still records association, lifecycle and truncation status
        when model validation fails before any research observer event exists.
        """
        with self._lock:
            try:
                self._identifiers(job)
                self._require_owner(owner_id)
                self._active.add(job.job_id)
                if self._enabled:
                    summary = {
                        "schema_version": 1, "run_id": self.run_id,
                        "logged_at_utc": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                        "session_id": job.session_id, "job_id": job.job_id, "owner_id": owner_id,
                        "state": job.state, "revision_before": job.revision,
                        "forensic_events": self._sequence.get(job.job_id, 0),
                        "forensic_stopped": self._stopped.get(job.job_id),
                        "diagnostics": record,
                    }
                    self._append(self._path(job, "diagnostic.json"), self._encoded(summary),
                                 file_limit=self.max_file_bytes)
            except Exception:
                pass
            finally:
                self._active.discard(job.job_id)
                self._sequence.pop(job.job_id, None)
                self._stopped.pop(job.job_id, None)
                try:
                    self._prune()
                except OSError:
                    self._enabled = False

    def usage(self):
        """Measure actual bytes; no fixed per-question storage estimate exists."""
        with self._lock:
            try:
                self._prune()
                files, unmanaged_bytes, unmanaged_files = self._scan()
                managed_bytes = sum(item[1] for item in files)
                return {
                    "bytes": managed_bytes + unmanaged_bytes, "managed_bytes": managed_bytes,
                    "files": len(files), "unmanaged_bytes": unmanaged_bytes,
                    "unmanaged_files": unmanaged_files, "limit_bytes": self.max_bytes,
                    "file_limit_bytes": self.max_file_bytes, "retention_days": self.retention_days,
                    "enabled": self._enabled,
                }
            except OSError:
                self._enabled = False
                return {"bytes": None, "files": None, "limit_bytes": self.max_bytes,
                        "file_limit_bytes": self.max_file_bytes, "retention_days": self.retention_days,
                        "enabled": False}

    def _session_files(self, session_id):
        if not isinstance(session_id, str) or not _ID.fullmatch(session_id):
            raise ValueError("invalid_diagnostic_identity")
        self._prune()
        files, _, _ = self._scan()
        return sorted((path for path, _, _, _ in files if path.name.startswith(session_id + ".")),
                      key=lambda path: path.name)

    def export(self, session_id: str):
        """Return only the selected session's available diagnostic files."""
        with self._lock:
            exported = {}
            for path in self._session_files(session_id):
                descriptor, _ = self._open(path, os.O_RDONLY)
                with os.fdopen(descriptor, "rb") as source:
                    exported[path.name] = source.read(self.max_bytes + 1)
            return exported

    def add_to_archive(self, archive, session_id: str):
        """Stream exports into an operator-created ZIP without loading all bodies."""
        with self._lock:
            for path in self._session_files(session_id):
                descriptor, _ = self._open(path, os.O_RDONLY)
                with os.fdopen(descriptor, "rb") as source:
                    with archive.open("diagnostics/" + path.name, "w", force_zip64=True) as target:
                        while chunk := source.read(64 * 1024):
                            target.write(chunk)
