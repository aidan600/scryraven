"""Tracked loopback-only credentialed provider-execution broker.

Only this process reads the private environment file and handles provider
credentials.  Requests and responses use the versioned mechanical contract in
``scripts.provider_execution_contract``.  Raw provider objects remain local to
one adapter call and are discarded after normalization.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.provider_execution_contract import (
    BROKER_DEFAULT_PORT,
    BROKER_ENV_FILE_PATH_ENV_VAR,
    BROKER_HEALTH_PATH,
    BROKER_HOST,
    BROKER_MAX_REQUESTS_ENV_VAR,
    BROKER_RUN_PATH,
    BROKER_TOKEN_ENV_VAR,
    BROKER_TOKEN_HEADER,
    MODEL_GENERATE_OPERATION,
    SEARCH_QUERY_OPERATION,
    ProviderExecutionContractError,
    build_failure_response,
    build_success_response,
    normalize_search_provider_result,
    validate_provider_execution_request,
)

HOST = BROKER_HOST
DEFAULT_PORT = BROKER_DEFAULT_PORT
RUN_PATH = BROKER_RUN_PATH
HEALTH_PATH = BROKER_HEALTH_PATH
TOKEN_HEADER = BROKER_TOKEN_HEADER
TOKEN_ENV_VAR = BROKER_TOKEN_ENV_VAR
ENV_FILE_PATH_ENV_VAR = BROKER_ENV_FILE_PATH_ENV_VAR
MAX_REQUESTS_ENV_VAR = BROKER_MAX_REQUESTS_ENV_VAR
MAX_REQUEST_BODY_BYTES = 256_000

# Credential variable names intentionally exist only in the credential-owning
# broker process.  The helper and client have no copy of this mapping.
_PROVIDER_CREDENTIAL_ENV = {
    "openai": "OPENAI_API_KEY",
    "serper": "SERPER_API_KEY",
    "tavily": "TAVILY_API_KEY",
}

ProviderAdapter = Callable[[Mapping[str, Any], str], Mapping[str, Any]]


class BrokerExecutionError(ValueError):
    """Sanitized provider execution failure with exact attempt posture."""

    def __init__(self, failure_class: str, *, physical_attempt_count: int = 0) -> None:
        self.failure_class = failure_class
        self.physical_attempt_count = physical_attempt_count
        super().__init__(failure_class)


@dataclass(slots=True)
class BrokerSessionState:
    token: str
    credentials: Mapping[str, str]
    requests_remaining: int
    adapters: Mapping[tuple[str, str], ProviderAdapter]
    _lock: threading.Lock

    @classmethod
    def create(
        cls,
        *,
        token: str,
        credentials: Mapping[str, str],
        maximum_requests: int,
        adapters: Mapping[tuple[str, str], ProviderAdapter] | None = None,
    ) -> "BrokerSessionState":
        if not token or maximum_requests < 1:
            raise BrokerExecutionError("invalid_broker_session_configuration")
        return cls(
            token=token,
            credentials=dict(credentials),
            requests_remaining=maximum_requests,
            adapters=dict(adapters or default_provider_adapters()),
            _lock=threading.Lock(),
        )

    def reserve_request(self) -> bool:
        with self._lock:
            if self.requests_remaining <= 0:
                return False
            self.requests_remaining -= 1
            return True


class ProviderExecutionHandler(BaseHTTPRequestHandler):
    """HTTP boundary for one configured broker session."""

    session: BrokerSessionState

    def do_GET(self) -> None:  # noqa: N802
        if not self._is_loopback_peer():
            self._send_json(403, _anonymous_failure("loopback_only"))
            return
        if self.path != HEALTH_PATH:
            self._send_json(404, _anonymous_failure("not_found"))
            return
        self._send_json(
            200,
            {
                "status": "ready",
                "raw_provider_payload_retained": False,
                "raw_request_material_retained": False,
                "raw_response_material_retained": False,
                "raw_search_response_retained": False,
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        request_payload: dict[str, Any] | None = None
        if not self._is_loopback_peer():
            self._send_json(403, _anonymous_failure("loopback_only"))
            return
        if self.path != RUN_PATH:
            self._send_json(404, _anonymous_failure("not_found"))
            return
        if self.headers.get(TOKEN_HEADER) != self.session.token:
            self._send_json(403, _anonymous_failure("invalid_session"))
            return
        if not self.session.reserve_request():
            self._send_json(403, _anonymous_failure("maximum_requests_exhausted"))
            return
        try:
            request_payload = self._read_request()
            validated = validate_provider_execution_request(request_payload)
            response = execute_provider_request(
                validated,
                credentials=self.session.credentials,
                adapters=self.session.adapters,
            )
            self._send_json(200, response)
        except ProviderExecutionContractError as exc:
            self._send_json(
                400,
                build_failure_response(
                    request_payload=request_payload,
                    failure_class=exc.failure_class,
                    physical_attempt_count=0,
                ),
            )
        except BrokerExecutionError as exc:
            self._send_json(
                502,
                build_failure_response(
                    request_payload=request_payload,
                    failure_class=exc.failure_class,
                    physical_attempt_count=exc.physical_attempt_count,
                ),
            )
        except Exception:
            self._send_json(
                500,
                build_failure_response(
                    request_payload=request_payload,
                    failure_class="broker_internal_failure",
                    physical_attempt_count=0,
                ),
            )
        finally:
            request_payload = None

    def _read_request(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ProviderExecutionContractError("invalid_content_length") from exc
        if length < 2 or length > MAX_REQUEST_BODY_BYTES:
            raise ProviderExecutionContractError("request_body_size_out_of_bounds")
        try:
            decoded = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderExecutionContractError("request_body_must_be_json") from exc
        if not isinstance(decoded, dict):
            raise ProviderExecutionContractError("request_body_must_be_object")
        return decoded

    def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
        encoded = json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _is_loopback_peer(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def execute_provider_request(
    request_payload: Mapping[str, Any],
    *,
    credentials: Mapping[str, str],
    adapters: Mapping[tuple[str, str], ProviderAdapter] | None = None,
) -> dict[str, Any]:
    """Execute one explicit provider operation with bounded caller retries."""

    validated = validate_provider_execution_request(request_payload)
    route = (validated["provider"], validated["operation"])
    selected_adapters = adapters or default_provider_adapters()
    adapter = selected_adapters.get(route)
    if adapter is None:
        raise BrokerExecutionError("unsupported_provider_operation")
    credential = _required_provider_credential(
        validated["provider"],
        credentials=credentials,
    )
    maximum_attempts = validated["retry_cap"] + 1
    attempts = 0
    last_failure = "provider_execution_failed"
    while attempts < maximum_attempts:
        attempts += 1
        try:
            adapter_result = adapter(validated, credential)
            if validated["operation"] == SEARCH_QUERY_OPERATION:
                raw_results = adapter_result.get("results")
                if not isinstance(raw_results, list):
                    raise BrokerExecutionError(
                        "provider_response_invalid",
                        physical_attempt_count=attempts,
                    )
                normalized_results = [
                    normalize_search_provider_result(
                        item,
                        provider=validated["provider"],
                        result_rank=index,
                        provider_call_index=attempts,
                    )
                    for index, item in enumerate(
                        raw_results[: validated["max_results"]],
                        start=1,
                    )
                ]
                adapter_result = {}
                raw_results = []
                return build_success_response(
                    validated,
                    physical_attempt_count=attempts,
                    results=normalized_results,
                )

            output_text = adapter_result.get("output_text")
            input_tokens = adapter_result.get("input_tokens")
            output_tokens = adapter_result.get("output_tokens")
            adapter_result = {}
            return build_success_response(
                validated,
                physical_attempt_count=attempts,
                output_text=output_text if isinstance(output_text, str) else None,
                input_tokens=input_tokens if isinstance(input_tokens, int) else None,
                output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            )
        except BrokerExecutionError as exc:
            last_failure = exc.failure_class
            if exc.physical_attempt_count == 0:
                raise
        except ProviderExecutionContractError as exc:
            last_failure = exc.failure_class
        except Exception:
            last_failure = "provider_execution_failed"
    raise BrokerExecutionError(
        last_failure,
        physical_attempt_count=attempts,
    )


def default_provider_adapters() -> dict[tuple[str, str], ProviderAdapter]:
    return {
        ("serper", SEARCH_QUERY_OPERATION): _call_serper_search,
        ("tavily", SEARCH_QUERY_OPERATION): _call_tavily_search,
        ("openai", MODEL_GENERATE_OPERATION): _call_openai_model,
    }


def _call_serper_search(
    request_payload: Mapping[str, Any],
    credential: str,
) -> Mapping[str, Any]:
    import requests

    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": credential,
                "Content-Type": "application/json",
            },
            json={
                "q": request_payload["query"],
                "num": request_payload["max_results"],
            },
            timeout=request_payload["timeout_seconds"],
        )
        response.raise_for_status()
        raw = response.json()
    except requests.exceptions.Timeout as exc:
        raise BrokerExecutionError("provider_timeout", physical_attempt_count=1) from exc
    except Exception as exc:
        raise BrokerExecutionError("provider_request_failed", physical_attempt_count=1) from exc
    if not isinstance(raw, Mapping):
        raise BrokerExecutionError("provider_response_invalid", physical_attempt_count=1)
    organic = raw.get("organic")
    if not isinstance(organic, list):
        organic = []
    results = [
        {
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
            "date": item.get("date"),
            "rank": item.get("position"),
        }
        for item in organic
        if isinstance(item, Mapping)
    ]
    raw = {}
    organic = []
    return {"results": results}


def _call_tavily_search(
    request_payload: Mapping[str, Any],
    credential: str,
) -> Mapping[str, Any]:
    import requests

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": credential,
                "query": request_payload["query"],
                "search_depth": "basic",
                "topic": "general",
                "include_answer": False,
                "include_images": False,
                "include_raw_content": True,
                "max_results": request_payload["max_results"],
            },
            timeout=request_payload["timeout_seconds"],
        )
        response.raise_for_status()
        raw = response.json()
    except requests.exceptions.Timeout as exc:
        raise BrokerExecutionError("provider_timeout", physical_attempt_count=1) from exc
    except Exception as exc:
        raise BrokerExecutionError("provider_request_failed", physical_attempt_count=1) from exc
    if not isinstance(raw, Mapping):
        raise BrokerExecutionError("provider_response_invalid", physical_attempt_count=1)
    provider_results = raw.get("results")
    if not isinstance(provider_results, list):
        provider_results = []
    results = [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "snippet": item.get("content"),
            "raw_content": item.get("raw_content"),
            "date": item.get("published_date"),
        }
        for item in provider_results
        if isinstance(item, Mapping)
    ]
    raw = {}
    provider_results = []
    return {"results": results}


def _call_openai_model(
    request_payload: Mapping[str, Any],
    credential: str,
) -> Mapping[str, Any]:
    try:
        from openai import OpenAI
    except Exception as exc:
        raise BrokerExecutionError(
            "provider_client_unavailable",
            physical_attempt_count=0,
        ) from exc
    try:
        client_kwargs: dict[str, Any] = {
            "api_key": credential,
            "max_retries": 0,
            "timeout": request_payload["timeout_seconds"],
        }
        if request_payload.get("base_url"):
            client_kwargs["base_url"] = request_payload["base_url"]
        client = OpenAI(**client_kwargs)
        create_kwargs: dict[str, Any] = {
            "model": request_payload["model"],
            "instructions": request_payload["system_instructions"],
            "input": request_payload["input_prompt"],
            "max_output_tokens": request_payload["max_output_tokens"],
            "store": False,
        }
        if request_payload.get("reasoning_effort"):
            create_kwargs["reasoning"] = {
                "effort": request_payload["reasoning_effort"]
            }
        response = client.responses.create(**create_kwargs)
    except Exception as exc:
        if exc.__class__.__name__ == "APITimeoutError":
            raise BrokerExecutionError(
                "provider_timeout",
                physical_attempt_count=1,
            ) from exc
        raise BrokerExecutionError("provider_request_failed", physical_attempt_count=1) from exc
    output_text = getattr(response, "output_text", None)
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    if (
        not isinstance(output_text, str)
        or not output_text
        or not isinstance(input_tokens, int)
        or not isinstance(output_tokens, int)
        or input_tokens < 0
        or output_tokens < 0
    ):
        response = None
        output_text = None
        raise BrokerExecutionError(
            "provider_response_usage_or_output_missing",
            physical_attempt_count=1,
        )
    normalized = {
        "output_text": output_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    response = None
    return normalized


def load_private_environment_file(path: str | Path) -> dict[str, str]:
    """Parse the private environment only inside the broker process."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise BrokerExecutionError("environment_file_unavailable")
    try:
        lines = resolved.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise BrokerExecutionError("environment_file_unavailable") from exc
    values: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        name, separator, value = line.partition("=")
        if not separator:
            continue
        clean_name = name.strip()
        if clean_name not in _PROVIDER_CREDENTIAL_ENV.values():
            continue
        clean_value = value.strip()
        if (
            len(clean_value) >= 2
            and clean_value[0] == clean_value[-1]
            and clean_value[0] in {"'", '"'}
        ):
            clean_value = clean_value[1:-1]
        if clean_value:
            values[clean_name] = clean_value
    lines = []
    return values


def _required_provider_credential(
    provider: str,
    *,
    credentials: Mapping[str, str],
) -> str:
    credential_name = _PROVIDER_CREDENTIAL_ENV.get(provider)
    credential = credentials.get(credential_name or "")
    if not credential:
        raise BrokerExecutionError("missing_configuration")
    return credential


def _anonymous_failure(failure_class: str) -> dict[str, Any]:
    return build_failure_response(
        request_payload=None,
        failure_class=failure_class,
        physical_attempt_count=0,
    )


def create_server(
    *,
    port: int,
    session: BrokerSessionState,
) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredProviderExecutionHandler",
        (ProviderExecutionHandler,),
        {"session": session},
    )
    return ThreadingHTTPServer((HOST, port), handler)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the tracked loopback-only ScryRaven provider broker."
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    token = os.environ.get(TOKEN_ENV_VAR, "")
    env_file_path = os.environ.get(ENV_FILE_PATH_ENV_VAR, "")
    try:
        maximum_requests = int(os.environ.get(MAX_REQUESTS_ENV_VAR, "1"))
        if args.port < 1 or args.port > 65535:
            raise BrokerExecutionError("invalid_broker_port")
        credentials = load_private_environment_file(env_file_path)
        session = BrokerSessionState.create(
            token=token,
            credentials=credentials,
            maximum_requests=maximum_requests,
        )
        server = create_server(port=args.port, session=session)
    except (ValueError, BrokerExecutionError):
        print("provider execution broker failed closed during startup", flush=True)
        return 2
    print("provider execution broker ready", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BrokerExecutionError",
    "BrokerSessionState",
    "DEFAULT_PORT",
    "ENV_FILE_PATH_ENV_VAR",
    "HEALTH_PATH",
    "HOST",
    "MAX_REQUESTS_ENV_VAR",
    "ProviderExecutionHandler",
    "RUN_PATH",
    "TOKEN_ENV_VAR",
    "TOKEN_HEADER",
    "create_server",
    "default_provider_adapters",
    "execute_provider_request",
    "load_private_environment_file",
    "main",
]
