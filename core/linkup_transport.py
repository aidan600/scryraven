"""LinkUp keyword search and static Fetch transports."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

import requests

from core.exa_transport import DiscoveryCandidate
from core.transport import FetchedMaterial, post_provider_request

LINKUP_FETCH_URL = "https://api.linkup.so/v1/fetch"
LINKUP_SEARCH_URL = "https://api.linkup.so/v1/search"
LINKUP_API_KEY_ENV = "LINKUP_API_KEY"  # pragma: allowlist secret
DEFAULT_TIMEOUT_SECONDS = 30.0
DISCOVERY_RESULT_COUNT = 10
LINKUP_FETCH_STRATEGY = "static_fetch"
LINKUP_FAILURE_CODES = frozenset({
    "linkup_timeout", "linkup_connection_failed", "linkup_endpoint_access_rejected",
    "linkup_endpoint_rate_limited", "linkup_endpoint_server_failed",
    "linkup_json_invalid", "linkup_response_invalid", "linkup_material_unavailable",
    "linkup_configuration_missing", "linkup_transport_failed",
})


class LinkupTransportError(RuntimeError):
    """Only fixed safe diagnostics cross the transport boundary."""


def fetch_linkup(
    selected_url: str, *, api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS, post: Callable[..., Any] | None = None,
) -> FetchedMaterial:
    """Fetch static readable material for one exact selected public URL."""
    url = _required_url(selected_url)
    payload = _post_linkup(LINKUP_FETCH_URL, {"url": url}, api_key, timeout_seconds, post)
    text = payload.get("markdown")
    if not isinstance(text, str) or not text.strip():
        text = payload.get("content")
    if not isinstance(text, str) or not text.strip():
        raise LinkupTransportError("linkup_material_unavailable")
    return FetchedMaterial(url, text)


def search_linkup(
    query: str, *, api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS, post: Callable[..., Any] | None = None,
    on_dispatch: Callable[[str], None] | None = None,
) -> list[DiscoveryCandidate]:
    """Send one keyword lookup and return navigation candidates."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be non-empty text")
    payload = _post_linkup(
        LINKUP_SEARCH_URL,
        {"q": query, "depth": "fast", "outputType": "searchResults", "maxResults": DISCOVERY_RESULT_COUNT},
        api_key, timeout_seconds, post, on_dispatch=on_dispatch,
    )
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise LinkupTransportError("linkup_response_invalid")
    candidates = []
    for row in rows:
        if not isinstance(row, Mapping) or row.get("type") != "text":
            continue
        try:
            url = _required_url(row.get("url"))
        except ValueError:
            continue
        if len(url) > 2048:
            continue
        title = _navigation_text(row.get("name"), 300)
        snippet = _navigation_text(row.get("content"), 500)
        candidates.append(DiscoveryCandidate(title, url, snippet))
        if len(candidates) == DISCOVERY_RESULT_COUNT:
            break
    return candidates


def _navigation_text(value: Any, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _post_linkup(
    endpoint: str, body: dict, api_key: str | None, timeout_seconds: float,
    post: Callable[..., Any] | None, *, on_dispatch: Callable[[str], None] | None = None,
) -> Mapping:
    token = api_key if api_key is not None else os.getenv(LINKUP_API_KEY_ENV)
    if not isinstance(token, str) or not token.strip():
        raise LinkupTransportError("linkup_configuration_missing")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        raise ValueError("timeout_seconds must be positive") from None
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    if on_dispatch is not None:
        try:
            on_dispatch(body["q"])
        except Exception:
            pass  # Optional activity cannot prevent dispatch.
    try:
        response = (post or post_provider_request)(
            endpoint,
            json=body,
            headers={"Authorization": f"Bearer {token.strip()}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise LinkupTransportError("linkup_timeout") from None
    except requests.exceptions.ConnectionError:
        raise LinkupTransportError("linkup_connection_failed") from None
    except requests.exceptions.HTTPError as exc:
        # These are LinkUp API endpoint statuses, not target-site diagnoses.
        status = getattr(exc.response, "status_code", None)
        code = "linkup_transport_failed"
        if type(status) is int:
            if status in {401, 403}:
                code = "linkup_endpoint_access_rejected"
            elif status == 429:
                code = "linkup_endpoint_rate_limited"
            elif 500 <= status <= 599:
                code = "linkup_endpoint_server_failed"
        raise LinkupTransportError(code) from None
    except Exception:
        raise LinkupTransportError("linkup_transport_failed") from None
    try:
        payload = response.json()
    except ValueError:
        raise LinkupTransportError("linkup_json_invalid") from None
    except Exception:
        raise LinkupTransportError("linkup_transport_failed") from None
    if not isinstance(payload, Mapping):
        raise LinkupTransportError("linkup_response_invalid")
    return payload


def _required_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("selected_url must be an absolute public http(s) URL")
    url = value.strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise ValueError("selected_url must be an absolute public http(s) URL") from None
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password):
        raise ValueError("selected_url must be an absolute public http(s) URL")
    return url
