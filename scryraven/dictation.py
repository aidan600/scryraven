"""Bounded, transient audio transcription for the Reading Room composer."""

from __future__ import annotations

import json
import os
from collections import deque
from contextlib import contextmanager
from struct import Struct
from threading import Lock
from time import monotonic

import requests
from urllib3.util import Timeout

from scryraven.chatgpt_plan.http import response_deadline
from scryraven.model import ModelError

MAX_SECONDS = 60
_SAMPLE_RATE = 16_000
_MIN_FRAMES = _SAMPLE_RATE // 4
_PCM_HEADER = Struct("<4sI4s4sIHHIIHH4sI")
MAX_AUDIO_BYTES = _PCM_HEADER.size + MAX_SECONDS * _SAMPLE_RATE * 2
API_UNAVAILABLE = "Dictation is unavailable without OpenAI API access."
BILLING_REQUIRED = "Authorize OpenAI API billing in Run Settings to use dictation."
_MAX_ATTEMPTS = 30
_ATTEMPT_WINDOW_SECONDS = 24 * 60 * 60
_MAX_ACTIVE = 2
_REQUEST_SECONDS = 35
_MAX_RESPONSE_BYTES = 128 * 1024


class TranscriptionError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


def available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def validate_audio(audio: bytes) -> None:
    """Check the exact format emitted by the browser, counting real PCM frames."""
    data_bytes = len(audio) - _PCM_HEADER.size
    if data_bytes < _MIN_FRAMES * 2:
        raise TranscriptionError("The recording was too short. Try speaking for a little longer.", 400)
    if len(audio) > MAX_AUDIO_BYTES:
        raise TranscriptionError(f"Record up to {MAX_SECONDS} seconds at a time.", 413)
    expected = (b"RIFF", len(audio) - 8, b"WAVE", b"fmt ", 16, 1, 1, _SAMPLE_RATE,
                _SAMPLE_RATE * 2, 2, 16, b"data", data_bytes)
    if data_bytes % 2 or _PCM_HEADER.unpack_from(audio) != expected:
        raise TranscriptionError("This recording format could not be read.", 400)


class TranscriptionSlots:
    """Separate process-local cost and concurrency limits for dictation only."""

    def __init__(self):
        self.lock = Lock()
        self.attempts: dict[str, deque[float]] = {}
        self.active: set[str] = set()

    @contextmanager
    def reserve(self, principal: str):
        with self.lock:
            if principal in self.active or len(self.active) >= _MAX_ACTIVE:
                raise TranscriptionError("Dictation is busy. Try again in a moment.", 429)
            now = monotonic()
            attempts = self.attempts.setdefault(principal, deque())
            while attempts and now - attempts[0] >= _ATTEMPT_WINDOW_SECONDS:
                attempts.popleft()
            if len(attempts) >= _MAX_ATTEMPTS:
                raise TranscriptionError("You reached the dictation limit. Try again later or type your question.", 429)
            attempts.append(now)
            self.active.add(principal)
        try:
            yield
        finally:
            with self.lock:
                self.active.remove(principal)


def transcribe(audio: bytes) -> str:
    """Send one authenticated file request; discard both audio and response on return."""
    token = os.getenv("OPENAI_API_KEY", "").strip()
    if not token:
        raise TranscriptionError(API_UNAVAILABLE, 503)
    try:
        with requests.Session() as session:
            session.trust_env = False
            end = monotonic() + _REQUEST_SECONDS
            with session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {token}"},
                data={"model": "gpt-transcribe"},
                files={"file": ("dictation.wav", audio, "audio/wav")},
                timeout=Timeout(total=_REQUEST_SECONDS, connect=5, read=_REQUEST_SECONDS),
                stream=True, allow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise TranscriptionError("OpenAI could not transcribe this recording. Try again.", 502)
                with response_deadline(response, end - monotonic()):
                    content = bytearray()
                    for chunk in response.iter_content(chunk_size=4096):
                        content.extend(chunk)
                        if len(content) > _MAX_RESPONSE_BYTES:
                            raise ValueError("transcript_response_too_large")
                payload = json.loads(content)
                if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
                    raise ValueError("invalid_transcript")
                return payload["text"].strip()
    except (requests.Timeout, ModelError):
        raise TranscriptionError("Dictation timed out. Try recording again.", 504) from None
    except (requests.RequestException, ValueError, RecursionError):
        raise TranscriptionError("The transcription could not be received. Try recording again.", 502) from None
