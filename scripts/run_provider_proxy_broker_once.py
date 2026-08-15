"""Start, use, and stop one tracked provider-execution broker session.

The helper validates but never opens the private environment file.  The file
path is supplied only to the broker child.  The temporary session token is
supplied only through separate broker/client child environments and never argv.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import request_provider_proxy_broker as client  # noqa: E402
from scripts.provider_execution_contract import (  # noqa: E402
    BROKER_ENV_FILE_PATH_ENV_VAR,
    BROKER_HEALTH_PATH,
    BROKER_MAX_REQUESTS_ENV_VAR,
    BROKER_RUN_PATH,
    BROKER_TOKEN_ENV_VAR,
)

TRACKED_BROKER_PATH = ROOT / "scripts" / "provider_execution_broker.py"
TRACKED_CLIENT_PATH = ROOT / "scripts" / "request_provider_proxy_broker.py"
READINESS_TIMEOUT_SECONDS = 10.0


class ProviderExecutionOperatorError(ValueError):
    """Raised when the local one-session operator flow must fail closed."""


ProviderProxyOperatorError = ProviderExecutionOperatorError


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    broker_process: subprocess.Popen[bytes] | None = None
    token: str | None = None
    try:
        if not args.confirm_provider_call:
            raise ProviderExecutionOperatorError("provider_call_confirmation_required")
        if not client._is_loopback_broker_url(args.broker_url):
            raise ProviderExecutionOperatorError("broker_url_must_be_loopback_http")
        output_path = client._resolve_output_path(args.output)
        client.prepare_output_path_for_sanitized_write(output_path)
        env_file_path = normalize_environment_file_path(args.env_file)
        token = generate_temporary_broker_token()
        broker_process = start_tracked_broker(
            broker_env=broker_environment(
                token=token,
                env_file_path=env_file_path,
                maximum_requests=args.maximum_requests,
                process_env=os.environ,
            ),
            port=_broker_port(args.broker_url),
        )
        wait_for_broker_readiness(
            broker_process,
            broker_url=args.broker_url,
            timeout_seconds=args.readiness_timeout_seconds,
        )
        rc = run_generic_provider_client(
            client_argv=_client_argv(args),
            client_env=client_environment(
                token=token,
                process_env=os.environ,
            ),
            timeout_seconds=args.timeout_seconds + args.readiness_timeout_seconds + 30.0,
        )
    except client.OutputHygieneError as exc:
        client.print_output_hygiene_failure_summary(exc)
        return 2
    except (
        ProviderExecutionOperatorError,
        client.ProviderExecutionClientError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        failure_class = (
            str(exc)
            if isinstance(
                exc,
                (ProviderExecutionOperatorError, client.ProviderExecutionClientError),
            )
            else "broker_child_process_failed"
        )
        print(
            f"provider-execution broker session failed closed: {failure_class}",
            file=sys.stderr,
        )
        return 2
    finally:
        if broker_process is not None:
            stop_tracked_broker(broker_process)
        token = None

    if rc == 0:
        print("provider-execution broker session completed")
    return rc


def _parser() -> argparse.ArgumentParser:
    parser = client._parser()
    parser.description = "Start the tracked loopback broker for one explicit provider execution."
    parser.add_argument(
        "--env-file",
        required=True,
        help="Private environment-file path passed only to the broker child.",
    )
    parser.add_argument(
        "--maximum-requests",
        type=int,
        default=1,
        choices=(1, 2, 6),
        help="Mechanical broker-session request fuse.",
    )
    parser.add_argument(
        "--readiness-timeout-seconds",
        type=float,
        default=READINESS_TIMEOUT_SECONDS,
    )
    return parser


def generate_temporary_broker_token() -> str:
    return secrets.token_urlsafe(32)


def normalize_environment_file_path(path: str | Path) -> Path:
    """Normalize and stat the path without opening or parsing the file."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise ProviderExecutionOperatorError("environment_file_unavailable")
    return resolved


def broker_environment(
    *,
    token: str,
    env_file_path: Path,
    maximum_requests: int,
    process_env: Mapping[str, str],
) -> dict[str, str]:
    if not token:
        raise ProviderExecutionOperatorError("invalid_broker_session")
    if maximum_requests not in {1, 2, 6}:
        raise ProviderExecutionOperatorError("maximum_requests_out_of_bounds")
    env = _minimal_child_environment(process_env)
    env.update(
        {
            BROKER_TOKEN_ENV_VAR: token,
            BROKER_ENV_FILE_PATH_ENV_VAR: str(env_file_path),
            BROKER_MAX_REQUESTS_ENV_VAR: str(maximum_requests),
        }
    )
    return env


def client_environment(
    *,
    token: str,
    process_env: Mapping[str, str],
) -> dict[str, str]:
    if not token:
        raise ProviderExecutionOperatorError("invalid_broker_session")
    env = _minimal_child_environment(process_env)
    env[BROKER_TOKEN_ENV_VAR] = token
    return env


def _minimal_child_environment(process_env: Mapping[str, str]) -> dict[str, str]:
    env = {"PYTHONIOENCODING": "utf-8"}
    for name in (
        "PATH",
        "Path",
        "SystemRoot",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "LOCALAPPDATA",
    ):
        value = process_env.get(name)
        if value:
            env[name] = value
    return env


def start_tracked_broker(
    *,
    broker_env: Mapping[str, str],
    port: int,
) -> subprocess.Popen[bytes]:
    if not TRACKED_BROKER_PATH.is_file():
        raise ProviderExecutionOperatorError("tracked_broker_unavailable")
    return subprocess.Popen(
        [
            sys.executable,
            str(TRACKED_BROKER_PATH),
            "--port",
            str(port),
        ],
        cwd=str(ROOT),
        env=dict(broker_env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_broker_readiness(
    process: subprocess.Popen[bytes],
    *,
    broker_url: str,
    timeout_seconds: float,
) -> None:
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ProviderExecutionOperatorError("readiness_timeout_out_of_bounds")
    deadline = time.monotonic() + timeout_seconds
    health_url = _health_url(broker_url)
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ProviderExecutionOperatorError("broker_startup_failed")
        try:
            with request.urlopen(health_url, timeout=0.25) as response:
                if response.status == 200:
                    return
        except (error.URLError, TimeoutError):
            pass
        time.sleep(0.05)
    raise ProviderExecutionOperatorError("broker_readiness_timeout")


def stop_tracked_broker(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_generic_provider_client(
    *,
    client_argv: list[str],
    client_env: Mapping[str, str],
    timeout_seconds: float,
) -> int:
    if not TRACKED_CLIENT_PATH.is_file():
        raise ProviderExecutionOperatorError("tracked_client_unavailable")
    completed = subprocess.run(
        [sys.executable, str(TRACKED_CLIENT_PATH), *client_argv],
        cwd=ROOT,
        env=dict(client_env),
        check=False,
        timeout=timeout_seconds,
    )
    return completed.returncode


def _client_argv(args: argparse.Namespace) -> list[str]:
    values: list[tuple[str, object | None]] = [
        ("--broker-url", args.broker_url),
        ("--provider", args.provider),
        ("--operation", args.operation),
        ("--model", args.model),
        ("--base-url", args.base_url),
        ("--query", args.query),
        ("--max-results", args.max_results),
        ("--system-instructions", args.system_instructions),
        ("--input-prompt", args.input_prompt),
        ("--reasoning-effort", args.reasoning_effort),
        ("--max-output-tokens", args.max_output_tokens),
        ("--maximum-input-tokens", args.maximum_input_tokens),
        ("--timeout-seconds", args.timeout_seconds),
        ("--retry-cap", args.retry_cap),
        ("--correlation-id", args.correlation_id),
        ("--requested-route-alias", args.requested_route_alias),
        (
            "--resolved-route-config-digest",
            args.resolved_route_config_digest,
        ),
        (
            "--ordinary-input-price-usd-per-million",
            args.ordinary_input_price_usd_per_million,
        ),
        (
            "--cached-input-price-usd-per-million",
            args.cached_input_price_usd_per_million,
        ),
        (
            "--output-price-usd-per-million",
            args.output_price_usd_per_million,
        ),
        ("--cost-ceiling-usd", args.cost_ceiling_usd),
        ("--expected-json-status", args.expected_json_status),
        ("--output", args.output),
    ]
    argv: list[str] = []
    for flag, value in values:
        if value is None:
            continue
        argv.extend([flag, str(value)])
    argv.append("--confirm-provider-call")
    return argv


def _broker_port(broker_url: str) -> int:
    parsed = parse.urlparse(broker_url)
    if parsed.path != BROKER_RUN_PATH or parsed.port is None:
        raise ProviderExecutionOperatorError("invalid_broker_url")
    return parsed.port


def _health_url(broker_url: str) -> str:
    parsed = parse.urlparse(broker_url)
    return parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            BROKER_HEALTH_PATH,
            "",
            "",
            "",
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ProviderExecutionOperatorError",
    "ProviderProxyOperatorError",
    "TRACKED_BROKER_PATH",
    "TRACKED_CLIENT_PATH",
    "broker_environment",
    "client_environment",
    "generate_temporary_broker_token",
    "main",
    "normalize_environment_file_path",
    "run_generic_provider_client",
    "start_tracked_broker",
    "stop_tracked_broker",
    "wait_for_broker_readiness",
]
