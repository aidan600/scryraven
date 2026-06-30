from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
DEFAULT_BROKER_URL = "http://127.0.0.1:8765/run"
TOKEN_ENV_VAR = "SCRYRAVEN_BROKER_TOKEN"
TOKEN_HEADER = "X-ScryRaven-Broker-Token"
REQUEST_KIND = "generic_provider_proxy_request"
OUTPUT_HYGIENE_DECISION = "BLOCKED_OUTPUT_HYGIENE"
OUTPUT_PREFLIGHT_SENTINEL = ".scryraven_provider_proxy_output_preflight.tmp"
SUPPORTED_PROVIDERS = frozenset({"serper"})
SUPPORTED_OPERATIONS = frozenset({"search"})
MAX_RESULTS_CAP = 10

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
        "auth_header",
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


class ProviderProxyClientError(ValueError):
    """Raised when the generic provider-proxy request or response is unsafe."""


class OutputHygieneError(ProviderProxyClientError):
    """Raised when sanitized output storage is unavailable before live contact."""

    def __init__(
        self,
        *,
        reason: str,
        output_path: Path,
        error_type: str | None = None,
    ) -> None:
        self.summary = build_output_hygiene_failure_summary(
            output_path=output_path,
            reason=reason,
            error_type=error_type,
        )
        super().__init__(
            f"{OUTPUT_HYGIENE_DECISION}: {reason} at {self.summary['output_path']}"
        )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        token = args.token or os.environ.get(TOKEN_ENV_VAR)
        if not token:
            raise ProviderProxyClientError(
                f"provide --token or set {TOKEN_ENV_VAR} in the calling shell"
            )
        if not args.confirm_provider_call:
            raise ProviderProxyClientError(
                "pass --confirm-provider-call to acknowledge a live provider call"
            )
        if not _is_loopback_broker_url(args.broker_url):
            raise ProviderProxyClientError(
                f"refusing to send broker token to non-loopback URL: {args.broker_url}"
            )

        output_path = _resolve_output_path(args.output)
        prepare_output_path_for_sanitized_write(output_path)
        payload = build_provider_proxy_request(
            provider=args.provider,
            operation=args.operation,
            query=args.query,
            max_results=args.max_results,
        )
        status, broker_json = _post_broker_json(args.broker_url, token, payload)
        sanitized = sanitize_broker_response(
            broker_json,
            provider=payload["provider"],
            operation=payload["operation"],
        )
        rendered = json.dumps(sanitized, indent=2, sort_keys=True) + "\n"
        output_path.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        print(f"wrote sanitized provider-proxy response to {output_path}")
    except OutputHygieneError as exc:
        print_output_hygiene_failure_summary(exc)
        return 2
    except ProviderProxyClientError as exc:
        print(f"refusing provider-proxy broker request: {exc}", file=sys.stderr)
        return 2

    if status < 200 or status >= 300:
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="POST a generic provider-proxy request to a local broker."
    )
    parser.add_argument("--broker-url", default=DEFAULT_BROKER_URL)
    parser.add_argument("--provider", required=True, choices=sorted(SUPPORTED_PROVIDERS))
    parser.add_argument(
        "--operation",
        default="search",
        choices=sorted(SUPPORTED_OPERATIONS),
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument(
        "--token",
        help=f"Local broker token. Alternatively set {TOKEN_ENV_VAR}.",
    )
    parser.add_argument("--confirm-provider-call", action="store_true")
    parser.add_argument("--output", required=True)
    return parser


def build_provider_proxy_request(
    *,
    provider: str,
    operation: str,
    query: str,
    max_results: int,
) -> dict[str, Any]:
    clean_provider = _required_token(provider, "provider is required", limit=80)
    clean_operation = _required_token(operation, "operation is required", limit=80)
    clean_query = _required_token(query, "query is required", limit=500)
    if clean_provider not in SUPPORTED_PROVIDERS:
        raise ProviderProxyClientError("provider is not supported")
    if clean_operation not in SUPPORTED_OPERATIONS:
        raise ProviderProxyClientError("operation is not supported")
    clean_max_results = _bounded_max_results(max_results)
    return {
        "request_kind": REQUEST_KIND,
        "provider": clean_provider,
        "operation": clean_operation,
        "query": clean_query,
        "max_results": clean_max_results,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def sanitize_broker_response(
    response_json: Mapping[str, Any],
    *,
    provider: str,
    operation: str,
) -> dict[str, Any]:
    response = _safe_mapping(response_json)
    _reject_forbidden_keys(response, context="broker response")
    if response.get("raw_provider_payload_retained") is not False:
        raise ProviderProxyClientError("broker response must not retain raw provider payloads")
    if response.get("raw_search_response_retained") is not False:
        raise ProviderProxyClientError("broker response must not retain raw search responses")
    raw_results = response.get("results", [])
    if not isinstance(raw_results, list):
        raise ProviderProxyClientError("broker response results must be a list")
    results = [
        normalize_provider_result(result, default_rank=index, default_call_index=index)
        for index, result in enumerate(raw_results, start=1)
    ]
    return {
        "request_kind": REQUEST_KIND,
        "provider": _required_token(provider, "provider is required", limit=80),
        "operation": _required_token(operation, "operation is required", limit=80),
        "result_count": len(results),
        "results": results,
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def prepare_output_path_for_sanitized_write(path: Path) -> Path:
    """Create and prove the output directory before broker/provider contact."""

    try:
        _require_output_path(path)
        output_dir = path.parent
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OutputHygieneError(
                reason="could_not_create_output_directory",
                output_path=path,
                error_type=exc.__class__.__name__,
            ) from exc
        if not output_dir.is_dir():
            raise OutputHygieneError(
                reason="output_directory_path_is_not_a_directory",
                output_path=path,
            )
        if path.exists() and path.is_dir():
            raise OutputHygieneError(
                reason="output_file_path_is_a_directory",
                output_path=path,
            )
        sentinel = output_dir / OUTPUT_PREFLIGHT_SENTINEL
        if sentinel.exists():
            raise OutputHygieneError(
                reason="output_preflight_sentinel_already_exists",
                output_path=path,
            )
        try:
            sentinel.write_text("", encoding="utf-8")
        except OSError as exc:
            raise OutputHygieneError(
                reason="output_directory_not_writable",
                output_path=path,
                error_type=exc.__class__.__name__,
            ) from exc
        try:
            sentinel.unlink()
        except OSError as exc:
            raise OutputHygieneError(
                reason="output_preflight_sentinel_cleanup_failed",
                output_path=path,
                error_type=exc.__class__.__name__,
            ) from exc
        return path
    except ProviderProxyClientError:
        raise
    except OSError as exc:
        raise OutputHygieneError(
            reason="output_hygiene_preflight_failed",
            output_path=path,
            error_type=exc.__class__.__name__,
        ) from exc


def build_output_hygiene_failure_summary(
    *,
    output_path: Path,
    reason: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    return _without_empty(
        {
            "decision": OUTPUT_HYGIENE_DECISION,
            "output_path": _safe_output_path(output_path),
            "output_directory": _safe_output_path(output_path.parent),
            "sanitized_reason": _clean_token(reason, limit=120),
            "error_type": _clean_token(error_type, limit=120),
            "broker_invoked": False,
            "provider_client_invoked": False,
            "live_provider_called": False,
            "raw_provider_payload_retained": False,
            "raw_search_response_retained": False,
        }
    )


def print_output_hygiene_failure_summary(exc: OutputHygieneError) -> None:
    print(json.dumps(exc.summary, indent=2, sort_keys=True), file=sys.stderr)


def normalize_provider_result(
    result: Mapping[str, Any],
    *,
    default_rank: int,
    default_call_index: int,
) -> dict[str, Any]:
    raw = _safe_mapping(result)
    _reject_forbidden_keys(raw, context="provider result")
    unknown = sorted(set(raw) - ALLOWED_RESULT_KEYS)
    if unknown:
        raise ProviderProxyClientError(
            "provider result contains unsupported fields: " + ", ".join(unknown)
        )
    title = _required_token(
        raw.get("title"),
        "provider result requires title",
        limit=220,
    )
    url = _required_url(raw.get("url") or raw.get("link"))
    domain = _clean_domain(raw.get("domain")) or _domain_from_url(url)
    if not domain:
        raise ProviderProxyClientError("provider result requires domain")
    return _without_empty(
        {
            "title": title,
            "url": url,
            "domain": domain,
            "snippet": _clean_token(raw.get("snippet"), limit=500),
            "published_or_observed_date": _clean_token(
                raw.get("published_or_observed_date") or raw.get("date"),
                limit=80,
            ),
            "result_rank": _positive_int(
                raw.get("result_rank") or raw.get("rank") or default_rank,
                "provider result rank must be positive",
            ),
            "provider_call_index": _positive_int(
                raw.get("provider_call_index")
                or raw.get("call_index")
                or default_call_index,
                "provider result call index must be positive",
            ),
        }
    )


def _post_broker_json(
    broker_url: str,
    token: str,
    payload: Mapping[str, Any],
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    broker_request = request.Request(
        broker_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            TOKEN_HEADER: token,
        },
        method="POST",
    )
    try:
        with request.urlopen(broker_request, timeout=30) as response:
            return response.status, _decode_json_response(response.read())
    except error.HTTPError as exc:
        return exc.code, _decode_json_response(exc.read())
    except error.URLError as exc:
        return 1, {"error": "broker_request_failed", "detail": exc.reason.__class__.__name__}


def _decode_json_response(response_body: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderProxyClientError("broker returned non-JSON response") from exc
    if not isinstance(decoded, dict):
        raise ProviderProxyClientError("broker returned non-object JSON response")
    return decoded


def _is_loopback_broker_url(broker_url: str) -> bool:
    parsed = parse.urlparse(broker_url)
    return (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and bool(parsed.port)
    )


def _resolve_output_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _require_output_path(path: Path) -> None:
    output_root = OUTPUT_DIR.resolve()
    try:
        path.relative_to(output_root)
    except ValueError as exc:
        raise OutputHygieneError(
            reason="output_path_outside_repo_output_boundary",
            output_path=path,
        ) from exc


def _safe_output_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _reject_forbidden_keys(value: Any, *, context: str) -> None:
    keys = _collect_keys(value)
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
        raise ProviderProxyClientError(
            f"{context} contains raw/private fields: " + ", ".join(forbidden)
        )


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {_normalize_key(key) for key in value}
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list | tuple | set | frozenset):
        keys: set[str] = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def _safe_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _required_url(value: Any) -> str:
    url = _required_token(value, "provider result requires url", limit=700)
    parsed = parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderProxyClientError("provider result requires http(s) url")
    return url


def _required_token(value: Any, message: str, *, limit: int) -> str:
    text = _clean_token(value, limit=limit)
    if not text:
        raise ProviderProxyClientError(message)
    return text


def _clean_token(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    lowered = text.casefold()
    if any(marker in lowered for marker in ("api_key", "bearer ", "secret")):
        return "[redacted]"
    return text[:limit]


def _clean_domain(value: Any) -> str | None:
    text = _clean_token(value, limit=260)
    if not text:
        return None
    parsed = parse.urlparse(f"https://{text}" if "://" not in text else text)
    return (parsed.netloc or parsed.path).lower().strip("/")


def _domain_from_url(value: str) -> str | None:
    parsed = parse.urlparse(value)
    return parsed.netloc.lower() or None


def _bounded_max_results(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ProviderProxyClientError("max_results must be an integer") from exc
    if parsed < 1 or parsed > MAX_RESULTS_CAP:
        raise ProviderProxyClientError(f"max_results must be between 1 and {MAX_RESULTS_CAP}")
    return parsed


def _positive_int(value: Any, message: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ProviderProxyClientError(message) from exc
    if parsed <= 0:
        raise ProviderProxyClientError(message)
    return parsed


def _without_empty(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != [] and value != {}
    }


def _normalize_key(key: Any) -> str:
    return str(key or "").strip().casefold().replace("-", "_").replace(" ", "_")


if __name__ == "__main__":
    raise SystemExit(main())
