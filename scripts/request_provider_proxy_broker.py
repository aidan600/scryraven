"""Loopback client for the generic ScryRaven provider-execution broker.

The client knows no provider credential names and never reads an environment
file.  A temporary session token is accepted only from the process environment.
Model output text is consumed transiently and projected to digest/length before
anything is printed or written.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.provider_execution_contract import (
    BROKER_DEFAULT_PORT,
    BROKER_HOST,
    BROKER_RUN_PATH,
    BROKER_TOKEN_ENV_VAR,
    BROKER_TOKEN_HEADER,
    FALSE_RETENTION_FLAGS,
    MODEL_GENERATE_OPERATION,
    REQUEST_KIND,
    SEARCH_PROOF_KIND,
    SEARCH_QUERY_OPERATION,
    SUPPORTED_OPERATIONS,
    SUPPORTED_PROVIDERS,
    ProviderExecutionContractError,
    build_model_proof,
    build_model_request,
    build_search_request,
    validate_provider_execution_response,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
DEFAULT_BROKER_URL = f"http://{BROKER_HOST}:{BROKER_DEFAULT_PORT}{BROKER_RUN_PATH}"
TOKEN_ENV_VAR = BROKER_TOKEN_ENV_VAR
TOKEN_HEADER = BROKER_TOKEN_HEADER
OUTPUT_HYGIENE_DECISION = "BLOCKED_OUTPUT_HYGIENE"
OUTPUT_PREFLIGHT_SENTINEL = ".scryraven_provider_execution_output_preflight.tmp"
class ProviderExecutionClientError(ValueError):
    """Safe client-side failure without provider material."""

    def __init__(self, failure_class: str) -> None:
        self.failure_class = failure_class
        super().__init__(failure_class)


# Compatibility import surface for current generic-provider client consumers.
ProviderProxyClientError = ProviderExecutionClientError


class OutputHygieneError(ProviderExecutionClientError):
    """Raised when sanitized output storage is unavailable before contact."""

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
        super().__init__(OUTPUT_HYGIENE_DECISION)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    transient_response: dict[str, Any] | None = None
    try:
        token = os.environ.get(TOKEN_ENV_VAR)
        if not token:
            raise ProviderExecutionClientError("missing_broker_session")
        if not args.confirm_provider_call:
            raise ProviderExecutionClientError("provider_call_confirmation_required")
        if not _is_loopback_broker_url(args.broker_url):
            raise ProviderExecutionClientError("broker_url_must_be_loopback_http")
        output_path = _resolve_output_path(args.output)
        prepare_output_path_for_sanitized_write(output_path)
        payload = _request_from_args(args)
        status, broker_json = _post_broker_json(
            args.broker_url,
            token,
            payload,
        )
        transient_response = validate_provider_execution_response(
            broker_json,
            request_payload=payload,
        )
        if transient_response["status"] != "ok":
            raise ProviderExecutionClientError(
                str(
                    transient_response.get("failure_class")
                    or "provider_execution_failed"
                )
            )
        if status < 200 or status >= 300:
            raise ProviderExecutionClientError("broker_http_failure")
        durable = _durable_projection(
            transient_response,
            request_payload=payload,
            args=args,
        )
        output_path.write_text(
            json.dumps(durable, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(durable, indent=2, sort_keys=True))
        print("sanitized provider-execution output written")
        durable = {}
        return 0
    except OutputHygieneError as exc:
        print_output_hygiene_failure_summary(exc)
        return 2
    except (ProviderExecutionClientError, ProviderExecutionContractError) as exc:
        failure_class = getattr(exc, "failure_class", "provider_execution_failed")
        print(
            "provider execution failed closed: "
            f"requested_provider={getattr(args, 'provider', 'unknown')}, "
            f"category={failure_class}",
            file=sys.stderr,
        )
        if failure_class == "missing_configuration":
            print(
                "private operator action: ensure the broker environment file "
                "contains configuration for the requested provider",
                file=sys.stderr,
            )
        return 2
    finally:
        transient_response = None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute one explicit request through the local provider broker."
    )
    parser.add_argument("--broker-url", default=DEFAULT_BROKER_URL)
    parser.add_argument("--provider", required=True, choices=sorted(SUPPORTED_PROVIDERS))
    parser.add_argument("--operation", required=True, choices=sorted(SUPPORTED_OPERATIONS))
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--query")
    parser.add_argument("--max-results", type=int)
    parser.add_argument("--system-instructions", default="")
    parser.add_argument("--input-prompt")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--maximum-input-tokens", type=int)
    parser.add_argument("--timeout-seconds", type=float, required=True)
    parser.add_argument("--retry-cap", type=int, required=True)
    parser.add_argument("--correlation-id")
    parser.add_argument(
        "--requested-route-alias",
        choices=("fast", "smart", "embed"),
    )
    parser.add_argument("--resolved-route-config-digest")
    parser.add_argument("--input-price-usd-per-million")
    parser.add_argument("--output-price-usd-per-million")
    parser.add_argument("--cost-ceiling-usd", required=True)
    parser.add_argument("--expected-json-status")
    parser.add_argument("--output", required=True)
    parser.add_argument("--confirm-provider-call", action="store_true")
    return parser


def _request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    common = {
        "provider": args.provider,
        "timeout_seconds": args.timeout_seconds,
        "retry_cap": args.retry_cap,
        "correlation_id": args.correlation_id,
        "requested_route_alias": args.requested_route_alias,
        "resolved_route_config_digest": args.resolved_route_config_digest,
    }
    if args.operation == SEARCH_QUERY_OPERATION:
        if (
            args.model is not None
            or args.base_url is not None
            or args.input_prompt is not None
            or args.max_output_tokens is not None
            or args.maximum_input_tokens is not None
            or args.input_price_usd_per_million is not None
            or args.output_price_usd_per_million is not None
            or args.expected_json_status is not None
        ):
            raise ProviderExecutionClientError("search_operation_argument_mismatch")
        return build_search_request(
            **common,
            query=args.query,
            max_results=args.max_results,
        )
    if (
        args.query is not None
        or args.max_results is not None
        or args.maximum_input_tokens is None
        or args.input_price_usd_per_million is None
        or args.output_price_usd_per_million is None
    ):
        raise ProviderExecutionClientError("model_operation_argument_mismatch")
    return build_model_request(
        **common,
        model=args.model,
        base_url=args.base_url,
        system_instructions=args.system_instructions,
        input_prompt=args.input_prompt,
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
    )


def _durable_projection(
    response: Mapping[str, Any],
    *,
    request_payload: Mapping[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    if request_payload["operation"] == MODEL_GENERATE_OPERATION:
        return build_model_proof(
            response,
            request_payload=request_payload,
            maximum_input_tokens=args.maximum_input_tokens,
            input_price_usd_per_million=args.input_price_usd_per_million,
            output_price_usd_per_million=args.output_price_usd_per_million,
            cost_ceiling_usd=args.cost_ceiling_usd,
            expected_json_status=args.expected_json_status,
        )
    normalized = validate_provider_execution_response(
        response,
        request_payload=request_payload,
    )
    proof = {
        "schema_version": normalized["schema_version"],
        "proof_kind": SEARCH_PROOF_KIND,
        "provider": normalized["provider"],
        "operation": normalized["operation"],
        "status": normalized["status"],
        "result_count": len(normalized["results"]),
        "results": normalized["results"],
        "physical_attempt_count": normalized["physical_attempt_count"],
        "caller_authorized_cost_ceiling_usd": args.cost_ceiling_usd,
        **{flag: False for flag in FALSE_RETENTION_FLAGS},
    }
    if normalized.get("correlation_id") is not None:
        proof["correlation_id"] = normalized["correlation_id"]
    return proof


def request_provider_execution(
    *,
    broker_url: str,
    token: str,
    request_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one validated transient envelope to an in-process consumer."""

    if not token:
        raise ProviderExecutionClientError("missing_broker_session")
    if not _is_loopback_broker_url(broker_url):
        raise ProviderExecutionClientError("broker_url_must_be_loopback_http")
    status, response = _post_broker_json(broker_url, token, request_payload)
    normalized = validate_provider_execution_response(
        response,
        request_payload=request_payload,
    )
    if normalized["status"] != "ok":
        raise ProviderExecutionClientError(
            str(normalized.get("failure_class") or "provider_execution_failed")
        )
    if status < 200 or status >= 300:
        raise ProviderExecutionClientError("broker_http_failure")
    return normalized


def build_provider_proxy_request(
    *,
    provider: str,
    operation: str,
    query: str,
    max_results: int,
    timeout_seconds: float = 30.0,
    retry_cap: int = 0,
) -> dict[str, Any]:
    """Compatibility callable that emits only the installed request family."""

    if operation != SEARCH_QUERY_OPERATION:
        raise ProviderExecutionClientError("operation_must_be_search_query")
    return build_search_request(
        provider=provider,
        query=query,
        max_results=max_results,
        timeout_seconds=timeout_seconds,
        retry_cap=retry_cap,
    )


def sanitize_broker_response(
    response_json: Mapping[str, Any],
    *,
    provider: str,
    operation: str,
    request_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compatibility callable for strict response-envelope validation."""

    payload = request_payload or build_search_request(
        provider=provider,
        query="compatibility-validation-query",
        max_results=10,
        timeout_seconds=30.0,
        retry_cap=0,
    )
    if operation != payload["operation"]:
        raise ProviderExecutionClientError("operation_attestation_mismatch")
    return validate_provider_execution_response(
        response_json,
        request_payload=payload,
    )


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
            sentinel.unlink()
        except OSError as exc:
            raise OutputHygieneError(
                reason="output_directory_not_writable",
                output_path=path,
                error_type=exc.__class__.__name__,
            ) from exc
        return path
    except ProviderExecutionClientError:
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
    return {
        "decision": OUTPUT_HYGIENE_DECISION,
        "output_path": _safe_output_path(output_path),
        "output_directory": _safe_output_path(output_path.parent),
        "sanitized_reason": _safe_token(reason),
        "error_type": _safe_token(error_type),
        "broker_invoked": False,
        "provider_client_invoked": False,
        "live_provider_called": False,
        **{flag: False for flag in FALSE_RETENTION_FLAGS},
    }


def print_output_hygiene_failure_summary(exc: OutputHygieneError) -> None:
    print(json.dumps(exc.summary, indent=2, sort_keys=True), file=sys.stderr)


def _post_broker_json(
    broker_url: str,
    token: str,
    payload: Mapping[str, Any],
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(dict(payload)).encode("utf-8")
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
    timeout = float(payload.get("timeout_seconds", 30.0)) + 5.0
    try:
        with request.urlopen(broker_request, timeout=timeout) as response:
            return response.status, _decode_json_response(response.read())
    except error.HTTPError as exc:
        return exc.code, _decode_json_response(exc.read())
    except error.URLError as exc:
        raise ProviderExecutionClientError("broker_request_failed") from exc


def _decode_json_response(response_body: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderExecutionClientError("broker_returned_non_json") from exc
    if not isinstance(decoded, dict):
        raise ProviderExecutionClientError("broker_returned_non_object")
    return decoded


def _is_loopback_broker_url(broker_url: str) -> bool:
    parsed = parse.urlparse(broker_url)
    return (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and bool(parsed.port)
        and parsed.path == BROKER_RUN_PATH
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
    )


def _resolve_output_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _require_output_path(path: Path) -> None:
    try:
        path.relative_to(OUTPUT_DIR.resolve())
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


def _safe_token(value: Any) -> str | None:
    if value is None:
        return None
    return "".join(
        char if char.isalnum() or char in {"_", "-"} else "_"
        for char in str(value)
    )[:120]


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_BROKER_URL",
    "OUTPUT_HYGIENE_DECISION",
    "OUTPUT_PREFLIGHT_SENTINEL",
    "ProviderExecutionClientError",
    "ProviderProxyClientError",
    "REQUEST_KIND",
    "SEARCH_PROOF_KIND",
    "SUPPORTED_OPERATIONS",
    "SUPPORTED_PROVIDERS",
    "TOKEN_ENV_VAR",
    "TOKEN_HEADER",
    "build_output_hygiene_failure_summary",
    "build_provider_proxy_request",
    "main",
    "prepare_output_path_for_sanitized_write",
    "print_output_hygiene_failure_summary",
    "request_provider_execution",
    "sanitize_broker_response",
]
