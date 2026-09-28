"""Mechanical LinkUp static Fetch transport for one selected public URL."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlsplit

import requests

from core.transport import FetchedMaterial

LINKUP_FETCH_URL = "https://api.linkup.so/v1/fetch"
LINKUP_API_KEY_ENV = "LINKUP_API_KEY"  # pragma: allowlist secret
DEFAULT_TIMEOUT_SECONDS = 30.0
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
    token = api_key if api_key is not None else os.getenv(LINKUP_API_KEY_ENV)
    if not isinstance(token, str) or not token.strip():
        raise LinkupTransportError("linkup_configuration_missing")
    try:
        timeout = float(timeout_seconds)
    except (TypeError, ValueError):
        raise ValueError("timeout_seconds must be positive") from None
    if timeout <= 0:
        raise ValueError("timeout_seconds must be positive")
    try:
        response = (post or requests.post)(
            LINKUP_FETCH_URL,
            json={"url": url},
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
    text = payload.get("markdown")
    if not isinstance(text, str) or not text.strip():
        text = payload.get("content")
    if not isinstance(text, str) or not text.strip():
        raise LinkupTransportError("linkup_material_unavailable")
    return FetchedMaterial(url, text)


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
