"""Mechanical Serper Google Search transport for navigation candidates only."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

import requests

from core.exa_transport import DiscoveryCandidate

SERPER_SEARCH_URL = "https://google.serper.dev/search"
SERPER_API_KEY_ENV = "SERPER_API_KEY"  # pragma: allowlist secret
DEFAULT_TIMEOUT_SECONDS = 30.0
DISCOVERY_RESULT_COUNT = 10


class SerperTransportError(RuntimeError):
    """Only fixed safe diagnostics cross the transport boundary."""


def search_serper(
    query: str, *, api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    post: Callable[..., Any] | None = None,
) -> list[DiscoveryCandidate]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be non-empty text")
    token = api_key if api_key is not None else os.getenv(SERPER_API_KEY_ENV)
    if not isinstance(token, str) or not token.strip():
        raise SerperTransportError("serper_configuration_missing")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        raise ValueError("timeout_seconds must be positive") from None
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    try:
        response = (post or requests.post)(
            SERPER_SEARCH_URL,
            json={"q": query.strip(), "num": DISCOVERY_RESULT_COUNT},
            headers={"X-API-KEY": token.strip(), "Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        raise SerperTransportError("serper_transport_failed") from None
    if not isinstance(payload, Mapping):
        raise SerperTransportError("serper_response_invalid")
    rows = payload.get("organic", [])
    if not isinstance(rows, list):
        raise SerperTransportError("serper_results_invalid")
    candidates = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        url = _text(row.get("link"), 2048)
        if not url:
            continue
        title = _text(row.get("title"), 300)
        snippet = _text(row.get("snippet"), 500)
        date = _text(row.get("date"), 80)
        position = row.get("position")
        metadata = []
        if isinstance(position, int) and not isinstance(position, bool) and position > 0:
            metadata.append(f"position {position}")
        if date:
            metadata.append(date)
        context = " | ".join([*metadata, snippet] if snippet else metadata)
        candidates.append(DiscoveryCandidate(title, url, context, context_kind="navigation"))
    return candidates[:DISCOVERY_RESULT_COUNT]


def _text(value: Any, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""
