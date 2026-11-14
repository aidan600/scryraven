"""Concurrent external Read transports and conservative mechanical selection."""

from __future__ import annotations

import io
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter as _clock

from core.exa_transport import (
    DEFAULT_TIMEOUT_SECONDS as EXA_SOCKET_SECONDS,
)
from core.exa_transport import (
    EXA_API_KEY_ENV,
    ExaTransportError,
    fetch_exa,
)
from core.linkup_transport import (
    LINKUP_API_KEY_ENV,
    LINKUP_FAILURE_CODES,
    LinkupTransportError,
    fetch_linkup,
)
from core.transport import FetchedMaterial, post_provider_request

READ_PROVIDERS = ("linkup", "exa")
READ_WALL_SECONDS = 300.0
PEER_SECONDS = 2.5
_CLEANUP_SECONDS = 0.25
_COMPARISON_SECONDS = 0.10
_ROOT = Path(__file__).resolve().parents[1]
_EXA_FAILURE_CODES = {
    "exa_configuration_missing", "exa_transport_failed", "exa_response_invalid",
    "exa_results_invalid", "contents_material_unavailable",
}
_SAFE_WORKER_CODES = LINKUP_FAILURE_CODES | _EXA_FAILURE_CODES | {
    "read_deadline", "read_worker_failed", "unusable_fetch_material",
    "read_identity_mismatch", "read_access_challenge", "read_landing_page",
    "read_peer_window_elapsed",
}
_LEADING_MARKUP = re.compile(r"^(?:[#>*]+\s*|\*\*|__|<[^>]+>)+")
_CHALLENGE_TITLE = re.compile(
    r"^(?:just a moment|checking your browser(?: before accessing.*)?|access denied"
    r"|attention required(?:!|\s*\|\s*cloudflare)?|request blocked|forbidden"
    r"|verify (?:that )?you are human|security (?:check|verification)"
    r"|a required part of this site couldn['’]t load)[\s.!…]*$",
    re.IGNORECASE,
)
_ERROR_TITLE = re.compile(
    r"^(?:(?:error|http)\s*)?(?:403|404|429|500|502|503)(?:\s*[-:–]?\s*"
    r"(?:forbidden|not found|too many requests|internal server error|bad gateway|"
    r"service unavailable|page not found))?[\s.!]*$"
    r"|^(?:page not found|file not found|this page (?:does not exist|is unavailable)"
    r"|sign in to (?:continue|access this (?:content|article)))[\s.!]*$",
    re.IGNORECASE,
)
_CHALLENGE_DETAIL = re.compile(
    r"(?:enable javascript and cookies|verify (?:that )?you are (?:a )?human|"
    r"cloudflare ray id|checking your browser|complete (?:the|this) security check|"
    r"a required part of this site couldn['’]t load|"
    r"your browser is (?:unsupported|out of date)|request (?:was|has been) blocked)",
    re.IGNORECASE,
)
_ERROR_DETAIL = re.compile(
    r"(?:page (?:you are looking for|could not be found)|page (?:does not exist|was not found)"
    r"|return to (?:the )?home ?page|you must sign in|there was an error processing"
    r"|this page is (?:no longer|currently) available)",
    re.IGNORECASE,
)
_SITE_LOAD_INTERSTITIAL = re.compile(
    r"\ba required part of this site couldn['’]t load\b[.!]?",
    re.IGNORECASE,
)
_SITE_LOAD_GUIDANCE = re.compile(
    r"\b(?:browser extensions?|ad blockers?|enable javascript|browser settings|"
    r"unsupported browser|network issues?|please (?:check|disable|try|reload))\b",
    re.IGNORECASE,
)
_SITE_LOAD_QUOTATION = re.compile(r"\b(?:reports?|reported|investigat\w*|said|wrote|warning|message|users saw)\b",
                                  re.IGNORECASE)
_EMPTY_LANDING_BODY = re.compile(
    r"^(?:please )?(?:enable javascript (?:to (?:continue|run this (?:app|application)))|"
    r"you need to enable javascript to run this app|loading(?: content)?)[\s.!…]*$",
    re.IGNORECASE,
)
_WORDS_OR_TARGET = re.compile(r"\]\(|[^\W_]+", re.UNICODE)
_WORD_CELL = re.compile(r"[^\W_]+(?:\s+[^\W_]+)?", re.UNICODE)


@dataclass(frozen=True, slots=True)
class ReadAttempt:
    provider: str
    dispatched: bool
    charged: bool
    status: str
    code: str | None
    dispatch_offset_seconds: float | None
    elapsed_seconds: float | None


@dataclass(frozen=True, slots=True)
class DualReadResult:
    provider: str | None
    material: FetchedMaterial | None
    attempts: tuple[ReadAttempt, ...]
    first_usable_provider: str | None
    selection: str


def configured_read_providers() -> tuple[str, ...]:
    """Return only configuration presence, in ordinary provider preference order."""
    return tuple(provider for provider, key in zip(
        READ_PROVIDERS, (LINKUP_API_KEY_ENV, EXA_API_KEY_ENV), strict=True,
    ) if os.environ.get(key, "").strip())


def validate_read_material(url: str, material: FetchedMaterial) -> str | None:
    """Check transport identity, empty material, and recognizable interstitials."""
    if not isinstance(material, FetchedMaterial) or not isinstance(material.readable_text, str):
        return "unusable_fetch_material"
    if material.requested_url != url:
        return "read_identity_mismatch"
    text = material.readable_text
    if not text.strip():
        return "unusable_fetch_material"
    # A site-load template may be collapsed onto one line with a heading.
    if len(text) <= 400 and (interstitial := _SITE_LOAD_INTERSTITIAL.search(text)):
        prefix = text[:interstitial.start()].strip()
        quoted = prefix.endswith(('"', "“", "'", "‘", "`")) or _SITE_LOAD_QUOTATION.search(prefix)
        if not quoted and (_SITE_LOAD_GUIDANCE.search(text, interstitial.end())
                           or (len(text) <= 250 and len(prefix) <= 80)):
            return "read_access_challenge"
    prefix = text[:1500]
    leading = []
    for line in prefix.splitlines()[:12]:
        line = _LEADING_MARKUP.sub("", line.strip()).strip("*_ ")
        if line and not line.startswith(("[", "![", "---")):
            leading.append(line)
    if not leading:
        return None
    if len(leading) == 1 and _EMPTY_LANDING_BODY.fullmatch(leading[0]):
        return "read_landing_page"
    # A challenge quoted in real article prose cannot trigger this check.
    title = leading[0]
    if (_CHALLENGE_TITLE.fullmatch(title)
            and (len(text) < 900 or _CHALLENGE_DETAIL.search(prefix))):
        return "read_access_challenge"
    if _ERROR_TITLE.fullmatch(title) and (len(text) < 900 or _ERROR_DETAIL.search(prefix)):
        return "read_landing_page"
    return None


class _ComparisonElapsed(Exception):
    pass


def _check_comparison_time(deadline):
    if _clock() >= deadline:
        raise _ComparisonElapsed


def _shingles(text, deadline):
    text = text.lower()
    shingles = set()
    previous = before_previous = None
    position = 0
    # Cache delimiter searches across neighboring malformed link openers.
    close = newline = -2
    for count in range(len(text)):
        if count % 1024 == 0:
            _check_comparison_time(deadline)
        token = _WORDS_OR_TARGET.search(text, position)
        if token is None:
            break
        position = token.end()
        word = token.group()
        if word == "](":
            if close != -1 and close < position:
                close = text.find(")", position)
            if newline != -1 and newline < position:
                newline = text.find("\n", position)
            if position < close <= position + 3000 and (newline < 0 or close < newline):
                position = close + 1
            continue
        if before_previous is not None:
            shingles.add((before_previous, previous, word))
        before_previous, previous = previous, word
    return shingles


def _cell_noise(text, deadline=math.inf):
    # OCR sometimes inserts a pipe between nearly every word of prose. A few
    # ordinary markdown tables are insufficient to establish this defect.
    total = 0
    for line_number, line in enumerate(text.splitlines()):
        if line_number % 1024 == 0:
            _check_comparison_time(deadline)
        run_cells = word_cells = 0
        for cell_number, cell in enumerate(line.split("|")[1:-1]):
            if cell_number % 1024 == 0:
                _check_comparison_time(deadline)
            cell = cell.strip()
            if len(cell) <= 26:
                run_cells += 1
                word_cells += bool(_WORD_CELL.fullmatch(cell))
            else:
                if run_cells >= 5:
                    total += word_cells
                run_cells = word_cells = 0
        if run_cells >= 5:
            total += word_cells
    return total


def _upgrade(first, peer, deadline=math.inf):
    # Large sources remain usable. Keep the first when a bounded comparison
    # cannot support replacing its original material with the peer's.
    if max(len(first), len(peer)) > 1_000_000 or first == peer:
        return None
    try:
        early, later = _shingles(first, deadline), _shingles(peer, deadline)
        if not early or not later:
            return None
        common = len(early & later)
        early_noise, later_noise = _cell_noise(first, deadline), _cell_noise(peer, deadline)
        _check_comparison_time(deadline)
    except _ComparisonElapsed:
        return None
    # Noise counts are compared against the amount of actual lexical material.
    # Normal table-heavy documents should not by themselves select a peer.
    if (common >= 0.85 * len(later) and common >= 0.78 * len(early)
            and early_noise >= max(40, 0.08 * len(early))
            and later_noise <= 0.25 * early_noise):
        return "cleaner_structure"
    if (common >= 0.97 * len(early)
            and len(later) - common >= max(30, 0.15 * len(early))
            and later_noise <= early_noise + max(8, 0.02 * len(early))):
        return "broader_original"
    return None


def _send(event):
    stream = sys.stdout.buffer
    stream.write(json.dumps(event, ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n")
    stream.flush()


def _worker(provider):
    _send({"kind": "ready"})
    try:
        command = json.loads(sys.stdin.readline())
        url, deadline, release_at = command["url"], command["deadline"], command["release_at"]
    except (KeyError, ValueError):
        return

    def exit_with_parent():
        # The parent holds this pipe open until this worker is reaped. An
        # unexpected parent exit closes it on both Windows and Linux.
        sys.stdin.readline()
        os._exit(1)

    threading.Thread(target=exit_with_parent, daemon=True).start()
    dispatched = False

    def post(endpoint, **kwargs):
        nonlocal dispatched
        time.sleep(max(0, release_at - _clock()))
        if dispatched or _clock() >= deadline:
            raise RuntimeError("read_dispatch_unavailable")
        dispatched = True
        _send({"kind": "dispatch", "time": _clock()})
        return post_provider_request(endpoint, **kwargs)

    fetch, socket_cap = ((fetch_linkup, READ_WALL_SECONDS) if provider == "linkup"
                         else (fetch_exa, EXA_SOCKET_SECONDS))
    started = _clock()
    if started >= deadline:
        _send({"kind": "result", "time": started, "code": "read_deadline"})
        os._exit(0)
    try:
        material = fetch(url, timeout_seconds=min(deadline - started, socket_cap), post=post)
        code = validate_read_material(url, material)
    except (LinkupTransportError, ExaTransportError) as error:
        material = None
        safe_codes = LINKUP_FAILURE_CODES if provider == "linkup" else _EXA_FAILURE_CODES
        code = str(error) if str(error) in safe_codes else "read_worker_failed"
    except Exception:
        material, code = None, "read_worker_failed"
    event = {"kind": "result", "time": _clock(), "code": code}
    body = b""
    if code is None:
        body = material.readable_text.encode("utf-8", errors="surrogatepass")
        event["bytes"] = len(body)
    _send(event)
    if body:
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()
    # Returning normally with a daemon blocked on the stdin buffer risks a
    # shutdown lock error. The result is already flushed and no work remains.
    os._exit(0)


def _worker_command(provider):
    return [sys.executable, "-m", "core.dual_read", provider]


class _Attempt:
    def __init__(self, provider):
        self.provider = provider
        self.process = None
        self.reader = None
        self.drained = False
        self.ready = self.released = False
        self.dispatched_at = self.completed_at = None
        self.material = self.code = self.status = None

    def launch(self, messages):
        try:
            self.process = subprocess.Popen(
                _worker_command(self.provider), cwd=_ROOT, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            self.finish("error", "read_worker_failed")
            return
        self.reader = threading.Thread(target=self.read, args=(messages,), daemon=True)
        self.reader.start()

    def read(self, messages):
        try:
            with self.process.stdout as stream:
                while line := stream.readline(1024):
                    try:
                        event = json.loads(line)
                    except ValueError:
                        # A kill can truncate a result, after any complete
                        # dispatch marker has already passed through this pipe.
                        continue
                    size = event.get("bytes")
                    if size is not None:
                        body = io.BytesIO()
                        while size and (chunk := stream.read(min(65536, size))):
                            body.write(chunk)
                            size -= len(chunk)
                        if size:
                            break
                        event["text"] = body.getvalue().decode("utf-8", errors="surrogatepass")
                    messages.put((self, event))
            self.drained = True
        except OSError:
            pass
        finally:
            messages.put((self, {"kind": "closed"}))

    def release(self, url, deadline, release_at):
        try:
            command = {"url": url, "deadline": deadline, "release_at": release_at}
            self.process.stdin.write(json.dumps(command).encode("ascii") + b"\n")
            self.process.stdin.flush()
            self.released = True
        except OSError:
            # A partial pipe write can still have reached the worker.
            self.released = True
            self.finish("error", "read_worker_failed")

    def handle(self, event, url, deadline, work_end):
        kind = event["kind"]
        if kind == "dispatch":
            self.dispatched_at = event["time"]
        if self.status is not None:
            return
        if kind == "ready":
            self.ready = True
        elif kind == "result":
            self.completed_at = event["time"]
            if self.completed_at > deadline:
                if self.completed_at > work_end:
                    self.finish("deadline", "read_deadline")
                else:
                    self.finish("cancelled", "read_peer_window_elapsed")
            elif event["code"] is not None:
                code = event["code"]
                self.finish("deadline" if code == "read_deadline" else "error",
                            code if code in _SAFE_WORKER_CODES else "read_worker_failed")
            else:
                self.material = FetchedMaterial(url, event["text"])
                self.finish("usable")
        elif kind == "closed":
            self.finish("error", "read_worker_failed")

    def finish(self, status, code=None):
        self.status, self.code = status, code
        if self.completed_at is None:
            self.completed_at = _clock()

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.kill()
            except ProcessLookupError:
                pass

    def reap(self, deadline):
        if self.process is None:
            return
        try:
            self.process.wait(timeout=max(0, deadline - _clock()))
            if self.reader is not None:
                self.reader.join(timeout=max(0, deadline - _clock()))
        except subprocess.TimeoutExpired:
            # The kill was already issued. Finish reaping even if another
            # Read never starts and the synchronous cleanup reserve expired.
            threading.Thread(target=self.process.wait, daemon=True).start()
            raise
        finally:
            # The worker watches this pipe and exits if the parent disappears.
            self.process.stdin.close()

    def receipt(self, started):
        # A flushed marker precedes every POST. A fully drained pipe without
        # a marker establishes that this worker could not have made a request.
        dispatched = self.dispatched_at is not None
        charged = dispatched or self.released and not self.drained
        return ReadAttempt(
            self.provider, dispatched, charged, self.status, self.code,
            self.dispatched_at - started if dispatched else None,
            self.completed_at - self.dispatched_at if dispatched else None,
        )


def _next_event(messages, deadline):
    try:
        return messages.get(timeout=max(0, deadline - _clock()))
    except queue.Empty:
        return None


def fetch_dual(url, *, timeout_seconds, providers=READ_PROVIDERS) -> DualReadResult:
    """Return one exact representation and safe receipts for all reserved arms."""
    providers = tuple(providers)
    if not providers or len(set(providers)) != len(providers) or set(providers) - set(READ_PROVIDERS):
        raise ValueError("invalid_read_providers")
    if not math.isfinite(timeout_seconds) or timeout_seconds < 0:
        raise ValueError("invalid_read_timeout")
    started = _clock()
    timeout_seconds = min(timeout_seconds, READ_WALL_SECONDS)
    end = started + timeout_seconds
    work_end = end - min(_CLEANUP_SECONDS + _COMPARISON_SECONDS, timeout_seconds / 4)
    messages = queue.Queue()
    attempts = [_Attempt(provider) for provider in providers]
    usable = []
    try:
        if _clock() < work_end:
            for attempt in attempts:
                if _clock() < work_end:
                    attempt.launch(messages)
                else:
                    attempt.finish("deadline", "read_deadline")
            startup_end = min(work_end, _clock() + 3)
            while any(not a.ready and a.status is None for a in attempts):
                event = _next_event(messages, startup_end)
                if event is None:
                    break
                attempt, message = event
                attempt.handle(message, url, work_end, work_end)
            release_at = min(work_end, _clock() + 0.02)
            for attempt in attempts:
                if attempt.status is None:
                    if attempt.ready and release_at < work_end:
                        attempt.release(url, work_end, release_at)
                    elif release_at >= work_end:
                        attempt.finish("deadline", "read_deadline")
                    else:
                        attempt.finish("error", "read_worker_failed")

        wait_end = work_end
        while any(a.status is None for a in attempts):
            event = _next_event(messages, wait_end)
            if event is None:
                break
            attempt, message = event
            attempt.handle(message, url, wait_end, work_end)
            if attempt.status == "usable" and attempt not in usable:
                usable.append(attempt)
                wait_end = min(wait_end, attempt.completed_at + PEER_SECONDS)
        for attempt in attempts:
            if attempt.status is None:
                if usable and wait_end < work_end:
                    attempt.finish("cancelled", "read_peer_window_elapsed")
                else:
                    attempt.finish("deadline", "read_deadline")
    finally:
        # Kill all losing workers before waiting on any one of them.
        cleanup_error = False
        for attempt in attempts:
            try:
                attempt.stop()
            except OSError:
                cleanup_error = True
        for attempt in attempts:
            try:
                attempt.reap(end)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_error = True
        if cleanup_error:
            # Each worker has already been killed. Never let an exceptional
            # cleanup path admit a winner or lose physical accounting.
            usable.clear()
        while (event := _next_event(messages, _clock())) is not None:
            attempt, message = event
            if message["kind"] == "dispatch":
                attempt.handle(message, url, work_end, work_end)

    receipts = tuple(attempt.receipt(started) for attempt in attempts)
    if not usable:
        return DualReadResult(None, None, receipts, None, "no_usable_material")
    first, *peers = sorted(usable, key=lambda attempt: attempt.completed_at)
    winner, selection = first, "first_usable"
    if peers and _clock() < end:
        peer = peers[0]
        reason = _upgrade(first.material.readable_text, peer.material.readable_text, end)
        if reason is not None:
            winner, selection = peer, reason
    return DualReadResult(winner.provider, winner.material, receipts, first.provider, selection)


if __name__ == "__main__":
    _worker(sys.argv[1])
