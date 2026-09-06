"""Mechanical Linkup discovery and Fetch donors.

This module deliberately owns transport mechanics only. It has no provider
selection, retry, cost, authority, custody, evidence, model, or answer logic.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import requests

LINKUP_SEARCH_URL = "https://api.linkup.so/v1/search"
LINKUP_FETCH_URL = "https://api.linkup.so/v1/fetch"
LINKUP_API_KEY_ENV = "LINKUP_API_KEY"  # pragma: allowlist secret
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_DISCOVERY_RESULT_COUNT = 6
MAX_DISCOVERY_RESULT_COUNT = 100
DISCOVERY_CONTEXT_MAX_CHARACTERS = 500

PostJSON = Callable[..., Any]


class LinkupTransportError(RuntimeError):
    """Raised when Linkup transport or response handling fails."""


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """A bounded navigation clue returned by standard Linkup discovery."""

    title: str
    url: str
    context: str


@dataclass(frozen=True, slots=True)
class FetchedMaterial:
    """Readable Linkup Fetch material mechanically associated with its request."""

    requested_url: str
    readable_text: str


def search_linkup(
    query: str,
    *,
    result_count: int = DEFAULT_DISCOVERY_RESULT_COUNT,
    api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    post: PostJSON | None = None,
) -> list[DiscoveryCandidate]:
    """Perform one standard Linkup search and normalize bounded clues."""

    normalized_query = _required_text(query, "query")
    bounded_count = _bounded_result_count(result_count)
    data = _post_json(
        LINKUP_SEARCH_URL,
        {
            "q": normalized_query,
            "depth": "standard",
            "outputType": "searchResults",
            "maxResults": bounded_count,
        },
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        post=post,
        operation="search",
    )
    raw_results = data.get("results", [])
    if raw_results is None:
        return []
    if not isinstance(raw_results, list):
        raise LinkupTransportError("Linkup search response results were not a list")

    candidates: list[DiscoveryCandidate] = []
    for raw_result in raw_results:
        if not isinstance(raw_result, Mapping):
            continue
        url = _text(raw_result.get("url"))
        if not url:
            continue
        title = _text(raw_result.get("name") or raw_result.get("title"))
        context = _bounded_text(
            raw_result.get("content") or raw_result.get("snippet"),
            DISCOVERY_CONTEXT_MAX_CHARACTERS,
        )
        candidates.append(
            DiscoveryCandidate(title=title, url=url, context=context)
        )
    return candidates[:bounded_count]


def fetch_linkup(
    selected_url: str,
    *,
    api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    post: PostJSON | None = None,
) -> FetchedMaterial:
    """Fetch one selected URL through Linkup and return readable material."""

    requested_url = _required_url(selected_url)
    data = _post_json(
        LINKUP_FETCH_URL,
        {"url": requested_url},
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        post=post,
        operation="fetch",
    )
    readable_text = _text(data.get("markdown")) or _text(data.get("content"))
    if not readable_text:
        raise LinkupTransportError(
            "Linkup fetch response contained no readable material"
        )
    return FetchedMaterial(
        requested_url=requested_url,
        readable_text=readable_text,
    )


def _post_json(
    url: str,
    payload: Mapping[str, Any],
    *,
    api_key: str | None,
    timeout_seconds: float,
    post: PostJSON | None,
    operation: str,
) -> Mapping[str, Any]:
    headers = _authorization_headers(api_key)
    timeout = _positive_timeout(timeout_seconds)
    sender = post or requests.post
    try:
        response = sender(
            url,
            json=dict(payload),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise LinkupTransportError(
            f"Linkup {operation} transport or response handling failed"
        ) from exc
    if not isinstance(data, Mapping):
        raise LinkupTransportError(
            f"Linkup {operation} response was not an object"
        )
    return data


def _authorization_headers(api_key: str | None) -> dict[str, str]:
    token = api_key if api_key is not None else os.getenv(LINKUP_API_KEY_ENV)
    if not isinstance(token, str) or not token.strip():
        raise LinkupTransportError(
            f"{LINKUP_API_KEY_ENV} is not configured"
        )
    return {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json",
    }


def _bounded_result_count(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("result_count must be an integer")
    if not 1 <= value <= MAX_DISCOVERY_RESULT_COUNT:
        raise ValueError(
            f"result_count must be between 1 and {MAX_DISCOVERY_RESULT_COUNT}"
        )
    return value


def _positive_timeout(value: float) -> float:
    timeout = float(value)
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    return timeout


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    return " ".join(value.split())


def _required_url(value: str) -> str:
    normalized = _required_text(value, "selected_url")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("selected_url must be an absolute http(s) URL")
    return normalized


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _bounded_text(value: Any, limit: int) -> str:
    return " ".join(_text(value).split())[:limit]


__all__ = [
    "DEFAULT_DISCOVERY_RESULT_COUNT",
    "DEFAULT_TIMEOUT_SECONDS",
    "DISCOVERY_CONTEXT_MAX_CHARACTERS",
    "DiscoveryCandidate",
    "FetchedMaterial",
    "LINKUP_API_KEY_ENV",
    "LINKUP_FETCH_URL",
    "LINKUP_SEARCH_URL",
    "LinkupTransportError",
    "MAX_DISCOVERY_RESULT_COUNT",
    "fetch_linkup",
    "search_linkup",
]
