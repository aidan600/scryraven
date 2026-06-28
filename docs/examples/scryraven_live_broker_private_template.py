"""
Non-secret private broker sketch for a durable ScryRaven provider proxy.

Do not run this file from the repository as-is. Copy the shape into a private
local location, load the broker token and provider credentials there, and keep
all secrets, raw provider payloads, private logs, and caches outside the repo.

The broker is not ScryRaven authority. It is only a tiny private key-holding
provider proxy for generic provider requests.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar, Mapping
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8765
MAX_RUNS = 1
MAX_RESULTS_CAP = 10
SUPPORTED_PROVIDERS = frozenset({"serper"})
SUPPORTED_OPERATIONS = frozenset({"search"})
TOKEN_HEADER = "X-ScryRaven-Broker-Token"
REQUEST_KIND = "generic_provider_proxy_request"

ALLOWED_RESULT_KEYS = frozenset(
    {
        "title",
        "url",
        "link",
        "domain",
        "snippet",
        "date",
        "published_or_observed_date",
        "rank",
        "result_rank",
        "call_index",
        "provider_call_index",
    }
)
RAW_OR_PRIVATE_KEYS = frozenset(
    {
        "api_key",
        "auth",
        "authorization",
        "cache",
        "db",
        "db_row",
        "env",
        "full_trace",
        "headers",
        "log",
        "logs",
        "prompt",
        "raw_content",
        "raw_page",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_response",
        "raw_search_response",
        "secret",
        "token",
    }
)


class PrivateBrokerHandler(BaseHTTPRequestHandler):
    runs_remaining: ClassVar[int] = MAX_RUNS
    one_shot_token: ClassVar[str] = "replace-in-private-copy"

    def do_POST(self) -> None:  # noqa: N802
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self._send_json(403, {"error": "loopback_only"})
            return
        if self.path != "/run":
            self._send_json(404, {"error": "not_found"})
            return
        if self.headers.get(TOKEN_HEADER) != self.one_shot_token:
            self._send_json(403, {"error": "invalid_token"})
            return
        if self.runs_remaining <= 0:
            self._send_json(403, {"error": "max_runs_exhausted"})
            return

        try:
            payload = self._read_json_body()
            request_payload = validate_provider_proxy_request(payload)
            self.runs_remaining -= 1
            provider_results = dispatch_provider_request(request_payload)
            self._send_json(
                200,
                {
                    "results": provider_results,
                    "raw_provider_payload_retained": False,
                    "raw_search_response_retained": False,
                },
            )
        except BrokerTemplateError as exc:
            self._send_json(400, {"error": str(exc)})

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        decoded = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(decoded, dict):
            raise BrokerTemplateError("request body must be a JSON object")
        return decoded

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        safe_payload = reject_raw_or_private_fields(payload, context="broker response")
        encoded = json.dumps(safe_payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


class BrokerTemplateError(ValueError):
    """Raised when the private broker sketch must fail closed."""


def validate_provider_proxy_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    reject_raw_or_private_fields(payload, context="broker request")
    if payload.get("request_kind") != REQUEST_KIND:
        raise BrokerTemplateError("unsupported_request_kind")
    provider = required_token(payload.get("provider"), "missing_provider", limit=80)
    operation = required_token(payload.get("operation"), "missing_operation", limit=80)
    query = required_token(payload.get("query"), "missing_query", limit=500)
    if provider not in SUPPORTED_PROVIDERS:
        raise BrokerTemplateError("unsupported_provider")
    if operation not in SUPPORTED_OPERATIONS:
        raise BrokerTemplateError("unsupported_operation")
    max_results = bounded_max_results(payload.get("max_results"))
    if payload.get("raw_provider_payload_retained") is not False:
        raise BrokerTemplateError("raw_provider_payload_retained_must_be_false")
    if payload.get("raw_search_response_retained") is not False:
        raise BrokerTemplateError("raw_search_response_retained_must_be_false")
    return {
        "provider": provider,
        "operation": operation,
        "query": query,
        "max_results": max_results,
    }


def dispatch_provider_request(request_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    provider = request_payload["provider"]
    operation = request_payload["operation"]
    if provider == "serper" and operation == "search":
        return call_serper_search_safely(
            query=str(request_payload["query"]),
            max_results=int(request_payload["max_results"]),
        )
    raise BrokerTemplateError("unsupported_provider_operation")


def call_serper_search_safely(*, query: str, max_results: int) -> list[dict[str, Any]]:
    """
    Private-copy implementation point.

    In the private broker copy only:
    - read the Serper credential from private environment/config;
    - perform one search operation;
    - immediately map the provider response into sanitized result dictionaries;
    - do not print or return raw payloads, headers, prompts, commands, logs, or secrets.
    """

    raise BrokerTemplateError("private_serper_adapter_not_configured")


def sanitize_provider_result(result: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    reject_raw_or_private_fields(result, context="provider result")
    unknown = sorted(set(result) - ALLOWED_RESULT_KEYS)
    if unknown:
        raise BrokerTemplateError("unsupported_result_fields:" + ",".join(unknown))
    title = required_token(result.get("title"), "result_missing_title", limit=220)
    url = required_url(result.get("url") or result.get("link"))
    domain = clean_domain(result.get("domain")) or domain_from_url(url)
    if not domain:
        raise BrokerTemplateError("result_missing_domain")
    return without_empty(
        {
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": clean_token(result.get("snippet"), limit=500),
            "published_or_observed_date": clean_token(
                result.get("published_or_observed_date") or result.get("date"),
                limit=80,
            ),
            "result_rank": positive_int(
                result.get("result_rank") or result.get("rank") or index,
                "result_rank_must_be_positive",
            ),
            "provider_call_index": positive_int(
                result.get("provider_call_index") or result.get("call_index") or index,
                "provider_call_index_must_be_positive",
            ),
        }
    )


def reject_raw_or_private_fields(value: Any, *, context: str) -> Any:
    keys = collect_keys(value)
    forbidden = sorted(
        key
        for key in keys
        if key in RAW_OR_PRIVATE_KEYS or key.startswith("raw_")
    )
    for allowed_false_flag in (
        "raw_provider_payload_retained",
        "raw_search_response_retained",
    ):
        if allowed_false_flag in forbidden:
            forbidden.remove(allowed_false_flag)
    if forbidden:
        raise BrokerTemplateError(
            f"{context}_contains_raw_or_private_fields:" + ",".join(forbidden)
        )
    return value


def collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {normalize_key(key) for key in value}
        for item in value.values():
            keys.update(collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(collect_keys(item))
        return keys
    return set()


def required_url(value: Any) -> str:
    url = required_token(value, "result_missing_url", limit=700)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise BrokerTemplateError("result_url_must_be_http")
    return url


def required_token(value: Any, message: str, *, limit: int) -> str:
    text = clean_token(value, limit=limit)
    if not text:
        raise BrokerTemplateError(message)
    return text


def clean_token(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in ("api_key", "bearer ", "secret")):
        return "[redacted]"
    return text[:limit]


def clean_domain(value: Any) -> str | None:
    text = clean_token(value, limit=260)
    if not text:
        return None
    parsed = urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def domain_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    return parsed.netloc.lower() or None


def bounded_max_results(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BrokerTemplateError("max_results_must_be_integer") from exc
    if parsed < 1 or parsed > MAX_RESULTS_CAP:
        raise BrokerTemplateError("max_results_out_of_bounds")
    return parsed


def positive_int(value: Any, message: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BrokerTemplateError(message) from exc
    if parsed <= 0:
        raise BrokerTemplateError(message)
    return parsed


def without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PrivateBrokerHandler)
    print(f"template provider proxy listening on http://{HOST}:{PORT}/run")
    server.serve_forever()


if __name__ == "__main__":
    main()
