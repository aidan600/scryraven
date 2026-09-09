"""One fixed Exa acquisition path. Transport mechanics, never evidence judgment."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import requests

EXA_SEARCH_URL = "https://api.exa.ai/search"
EXA_CONTENTS_URL = "https://api.exa.ai/contents"
EXA_API_KEY_ENV = "EXA_API_KEY"  # pragma: allowlist secret
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_DISCOVERY_RESULT_COUNT = 6
DISCOVERY_CONTEXT_SAFETY_LIMIT = 65_536
HIGHLIGHT_CHARACTERS = 4_000


class ExaTransportError(RuntimeError):
    """Only fixed safe diagnostics cross the transport boundary."""


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    title: str
    url: str
    context: str
    context_omitted_characters: int = 0
    context_kind: str = "navigation"


@dataclass(frozen=True, slots=True)
class FetchedMaterial:
    requested_url: str
    readable_text: str


def search_exa(
    query: str, *, result_count: int = DEFAULT_DISCOVERY_RESULT_COUNT,
    api_key: str | None = None, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    post: Callable[..., Any] | None = None,
) -> list[DiscoveryCandidate]:
    query = _required_text(query, "query")
    if isinstance(result_count, bool) or not isinstance(result_count, int) or not 1 <= result_count <= 100:
        raise ValueError("result_count must be an integer between 1 and 100")
    data = _post_json(EXA_SEARCH_URL, {
        "query": query, "type": "auto", "numResults": result_count,
        "contents": {"text": False, "highlights": {"query": query, "maxCharacters": HIGHLIGHT_CHARACTERS}},
    }, api_key, timeout_seconds, post)
    candidates = []
    for row in _results(data):
        url = _text(row.get("url"))
        if not url:
            continue
        highlights = row.get("highlights", [])
        if not isinstance(highlights, list):
            highlights = []
        # Preserve each actual highlight verbatim. The separator explicitly marks
        # separate provider selections, not a source-contiguous passage.
        context = "\n\n[Separate provider highlight; intervening context omitted]\n\n".join(
            item for item in highlights if isinstance(item, str) and item.strip()
        )
        omitted = len(context) if len(context) > DISCOVERY_CONTEXT_SAFETY_LIMIT else 0
        if omitted:
            context = "Provider material omitted by size guard; acquire this URL for context."
        candidates.append(DiscoveryCandidate(
            _text(row.get("title")), url, context, omitted,
            "provider_highlights" if context and not omitted else "navigation",
        ))
    return candidates[:result_count]


def fetch_exa(
    selected_url: str, *, api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS, post: Callable[..., Any] | None = None,
) -> FetchedMaterial:
    url = _required_text(selected_url, "selected_url")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("selected_url must be an absolute public http(s) URL")
    data = _post_json(EXA_CONTENTS_URL, {
        "ids": [url], "text": {"verbosity": "full"}, "highlights": False, "maxAgeHours": 0,
    }, api_key, timeout_seconds, post)
    for row in _results(data):
        if url not in {row.get("id"), row.get("url")}:
            continue
        content = row.get("text")
        if isinstance(content, str) and content.strip():
            return FetchedMaterial(url, content)
    raise ExaTransportError("contents_material_unavailable")


def _post_json(url, payload, api_key, timeout_seconds, post) -> Mapping[str, Any]:
    token = api_key if api_key is not None else os.getenv(EXA_API_KEY_ENV)
    if not isinstance(token, str) or not token.strip():
        raise ExaTransportError("exa_configuration_missing")
    timeout = float(timeout_seconds)
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    try:
        response = (post or requests.post)(
            url, json=payload, headers={"x-api-key": token.strip(), "Content-Type": "application/json"}, timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        raise ExaTransportError("exa_transport_failed") from None
    if not isinstance(data, Mapping):
        raise ExaTransportError("exa_response_invalid")
    return data


def _results(data: Mapping) -> list[Mapping]:
    rows = data.get("results", [])
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ExaTransportError("exa_results_invalid")
    return [row for row in rows if isinstance(row, Mapping)]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()
