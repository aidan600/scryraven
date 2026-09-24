"""Explicit local, source-bearing observer log for development dogfooding.

Records only events supplied by the ordinary research observer. It does not
collect model responses, provider payloads, or any additional product state.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


class ForensicLog:
    """Append observer events to a distinct JSONL file without affecting turns."""

    def __init__(self, path: str | Path, *, session_database: Path | None = None,
                 dogfood_log: Path | None = None):
        try:
            self.path = Path(path).expanduser().resolve()
            for other in (session_database, dogfood_log):
                if other is not None and (self.path == other or
                                          (self.path.exists() and other.exists() and
                                           self.path.samefile(other))):
                    raise OSError("forensic_log_path_collision")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8"):
                pass
        except (OSError, ValueError, RuntimeError):
            raise OSError("forensic_log_unavailable") from None
        self.session_database = session_database
        self.dogfood_log = dogfood_log
        self.run_id = uuid4().hex
        self._lock = Lock()
        self._sequence = 0
        self._enabled = True

    def _disable(self) -> None:
        if self._enabled:
            self._enabled = False
            print("Reading Room forensic diagnostics stopped: the local log could not be written.",
                  file=sys.stderr, flush=True)

    def disable(self) -> None:
        """Contain an unexpected failure in the Reading Room observer wrapper."""
        with self._lock:
            self._disable()

    def append(self, event: dict, *, session_id: str | None, revision_before: int) -> None:
        with self._lock:
            if not self._enabled:
                return
            try:
                record = {
                    "schema_version": 1,
                    "run_id": self.run_id,
                    "event_sequence": self._sequence + 1,
                    "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "attempted_turn": revision_before + 1,
                    "revision_before": revision_before,
                    "event": event,
                }
                line = json.dumps(record, ensure_ascii=True, separators=(",", ":"),
                                  allow_nan=False) + "\n"
                with self.path.open("a", encoding="utf-8") as target:
                    target_stat = os.fstat(target.fileno())
                    for other in (self.session_database, self.dogfood_log):
                        if other is None or not other.exists():
                            continue
                        other_stat = other.stat()
                        if (target_stat.st_ino and
                                (target_stat.st_dev, target_stat.st_ino)
                                == (other_stat.st_dev, other_stat.st_ino)):
                            raise OSError("forensic_log_path_collision")
                    target.write(line)
                self._sequence += 1
            except Exception:
                # Instrumentation must never invalidate a completed product turn.
                self._disable()
