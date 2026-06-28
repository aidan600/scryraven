from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import request_provider_proxy_broker as client  # noqa: E402

SERPER_KEY_ENV_VAR = "SERPER_API_KEY"
DEFAULT_PRIVATE_BROKER_PATH = (
    Path.home() / "ScryRavenLiveBroker" / "scryraven_live_broker.py"
)
LOCAL_PROVIDER_ENV_NAMES = frozenset({SERPER_KEY_ENV_VAR})


class ProviderProxyOperatorError(ValueError):
    """Raised when the local provider-proxy operator flow must fail closed."""


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    broker_process: subprocess.Popen[bytes] | None = None
    try:
        if not args.confirm_provider_call:
            raise ProviderProxyOperatorError(
                "pass --confirm-provider-call to acknowledge a live provider call"
            )
        client._require_output_path(client._resolve_output_path(args.output))
        token = generate_temporary_broker_token()
        env = broker_environment(
            provider=args.provider,
            token=token,
            env_file_paths=args.env_file,
            process_env=os.environ,
        )
        broker_path = _private_broker_path(args.private_broker_path)
        broker_process = start_private_broker(
            broker_path=broker_path,
            broker_env=env,
            python_executable=args.python_executable,
        )
        time.sleep(args.startup_wait_seconds)
        rc = run_generic_provider_client(
            broker_url=args.broker_url,
            provider=args.provider,
            operation=args.operation,
            query=args.query,
            max_results=args.max_results,
            output=args.output,
            token=token,
        )
    except (ProviderProxyOperatorError, client.ProviderProxyClientError) as exc:
        print(f"refusing provider-proxy broker operator run: {exc}", file=sys.stderr)
        return 2
    finally:
        if broker_process is not None:
            stop_private_broker(broker_process)

    if rc == 0:
        print("provider-proxy broker operator run completed; sanitized output written")
    return rc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one local generic provider-proxy broker request with a temporary "
            "broker token and sanitized output."
        )
    )
    parser.add_argument("--provider", required=True, choices=sorted(client.SUPPORTED_PROVIDERS))
    parser.add_argument(
        "--operation",
        default="search",
        choices=sorted(client.SUPPORTED_OPERATIONS),
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--broker-url", default=client.DEFAULT_BROKER_URL)
    parser.add_argument(
        "--private-broker-path",
        default=str(DEFAULT_PRIVATE_BROKER_PATH),
        help="Local private broker Python file outside this repository.",
    )
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        help="Optional local operator env file to read for provider credentials.",
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python executable used to start the private broker.",
    )
    parser.add_argument(
        "--startup-wait-seconds",
        type=float,
        default=1.5,
        help="Small local wait before the generic client posts to the broker.",
    )
    parser.add_argument("--confirm-provider-call", action="store_true")
    return parser


def generate_temporary_broker_token() -> str:
    return secrets.token_urlsafe(32)


def broker_environment(
    *,
    provider: str,
    token: str,
    env_file_paths: list[str],
    process_env: Mapping[str, str],
) -> dict[str, str]:
    provider_key = _provider_api_key(provider, env_file_paths, process_env)
    env: dict[str, str] = {
        client.TOKEN_ENV_VAR: token,
        SERPER_KEY_ENV_VAR: provider_key,
        "PYTHONIOENCODING": "utf-8",
    }
    for name in ("PATH", "SystemRoot", "TEMP", "TMP"):
        value = process_env.get(name)
        if value:
            env[name] = value
    return env


def start_private_broker(
    *,
    broker_path: Path,
    broker_env: Mapping[str, str],
    python_executable: str,
) -> subprocess.Popen[bytes]:
    if not broker_path.is_file():
        raise ProviderProxyOperatorError("private broker path does not exist")
    return subprocess.Popen(
        [python_executable, str(broker_path)],
        cwd=str(broker_path.parent),
        env=dict(broker_env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_private_broker(process: subprocess.Popen[bytes]) -> None:
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
    broker_url: str,
    provider: str,
    operation: str,
    query: str,
    max_results: int,
    output: str,
    token: str,
) -> int:
    return client.main(
        [
            "--broker-url",
            broker_url,
            "--provider",
            provider,
            "--operation",
            operation,
            "--query",
            query,
            "--max-results",
            str(max_results),
            "--output",
            output,
            "--token",
            token,
            "--confirm-provider-call",
        ]
    )


def load_env_file_values(path: str | Path) -> dict[str, str]:
    resolved = Path(path).expanduser()
    try:
        text = resolved.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ProviderProxyOperatorError("could not read operator env file") from exc
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        if key in LOCAL_PROVIDER_ENV_NAMES:
            values[key] = _strip_env_value(value)
    return values


def _provider_api_key(
    provider: str,
    env_file_paths: list[str],
    process_env: Mapping[str, str],
) -> str:
    if provider != "serper":
        raise ProviderProxyOperatorError("provider is not supported by the local operator")
    existing = process_env.get(SERPER_KEY_ENV_VAR)
    if existing:
        return existing
    for env_file_path in env_file_paths:
        value = load_env_file_values(env_file_path).get(SERPER_KEY_ENV_VAR)
        if value:
            return value
    raise ProviderProxyOperatorError(
        f"{SERPER_KEY_ENV_VAR} must be present in the operator process or explicit env file"
    )


def _private_broker_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _strip_env_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


if __name__ == "__main__":
    raise SystemExit(main())
