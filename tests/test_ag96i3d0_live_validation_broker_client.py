from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "request_live_validation_broker.py"


class BrokerHandler(BaseHTTPRequestHandler):
    response_status: ClassVar[int] = 200
    response_json: ClassVar[dict[str, Any]] = {"status": "accepted"}
    captured: ClassVar[dict[str, Any]] = {}

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).captured = {
            "path": self.path,
            "headers": dict(self.headers.items()),
            "json": json.loads(body.decode("utf-8")),
        }
        response = json.dumps(type(self).response_json).encode("utf-8")
        self.send_response(type(self).response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


class BrokerServer:
    def __init__(self, *, status: int, response_json: dict[str, Any]) -> None:
        BrokerHandler.response_status = status
        BrokerHandler.response_json = response_json
        BrokerHandler.captured = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), BrokerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}/run"

    @property
    def captured(self) -> dict[str, Any]:
        return dict(BrokerHandler.captured)

    def __enter__(self) -> "BrokerServer":
        self.thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _run_client(
    *args: str,
    token_env: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("SCRYRAVEN_BROKER_TOKEN", None)
    if token_env is not None:
        env["SCRYRAVEN_BROKER_TOKEN"] = token_env
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_client_refuses_without_token() -> None:
    result = _run_client(
        "--job-id",
        "ag96i3d0-official-current-once",
        "--confirm-live-provider-call",
    )

    assert result.returncode == 2
    assert "provide --token or SCRYRAVEN_BROKER_TOKEN" in result.stderr


def test_client_refuses_without_live_spend_confirmation() -> None:
    result = _run_client(
        "--job-id",
        "ag96i3d0-official-current-once",
        "--token",
        "one-shot-token",
    )

    assert result.returncode == 2
    assert "--confirm-live-provider-call" in result.stderr


def test_client_constructs_expected_post_body_and_token_header_only() -> None:
    with BrokerServer(status=200, response_json={"status": "accepted"}) as broker:
        result = _run_client(
            "--broker-url",
            broker.url,
            "--job-id",
            "ag96i3d0-official-current-once",
            "--token",
            "one-shot-token",
            "--confirm-live-provider-call",
        )

    assert result.returncode == 0
    assert broker.captured["path"] == "/run"
    assert broker.captured["json"] == {
        "job_id": "ag96i3d0-official-current-once",
        "confirm_live": True,
    }
    headers = _lower_headers(broker.captured["headers"])
    assert headers["x-scryraven-broker-token"] == "one-shot-token"
    assert "one-shot-token" not in result.stdout
    assert "one-shot-token" not in result.stderr
    assert "one-shot-token" not in json.dumps(broker.captured["json"])


def test_client_can_read_token_from_environment_without_printing_it() -> None:
    with BrokerServer(status=200, response_json={"status": "accepted"}) as broker:
        result = _run_client(
            "--broker-url",
            broker.url,
            "--job-id",
            "ag96i3d0-official-current-once",
            "--confirm-live-provider-call",
            token_env="env-one-shot-token",
        )

    assert result.returncode == 0
    headers = _lower_headers(broker.captured["headers"])
    assert headers["x-scryraven-broker-token"] == "env-one-shot-token"
    assert "env-one-shot-token" not in result.stdout
    assert "env-one-shot-token" not in result.stderr


def test_default_and_localhost_broker_urls_are_accepted() -> None:
    client = _load_client_module()

    assert client._is_loopback_broker_url(client.DEFAULT_BROKER_URL)
    assert client._is_loopback_broker_url("http://localhost:8765/run")
    assert client._is_loopback_broker_url("http://[::1]:8765/run")


def test_client_refuses_https_non_local_broker_url_before_warning() -> None:
    result = _run_client(
        "--broker-url",
        "https://example.com/run",
        "--job-id",
        "ag96i3d0-official-current-once",
        "--token",
        "one-shot-token",
        "--confirm-live-provider-call",
    )

    assert result.returncode == 2
    assert "non-local broker URL" in result.stderr
    assert "This request may spend one live provider/search call" not in result.stdout
    assert "one-shot-token" not in result.stdout
    assert "one-shot-token" not in result.stderr


def test_client_refuses_public_provider_broker_url_without_contacting_broker(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = _load_client_module()

    def unexpected_request(*_args: object, **_kwargs: object) -> tuple[int, dict[str, Any]]:
        raise AssertionError("broker request should not be attempted")

    monkeypatch.setattr(client, "_post_broker_json", unexpected_request)

    result = client.main(
        [
            "--broker-url",
            "http://api.search.brave.com/run",
            "--job-id",
            "ag96i3d0-official-current-once",
            "--token",
            "one-shot-token",
            "--confirm-live-provider-call",
        ]
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "non-local broker URL" in captured.err
    assert "This request may spend one live provider/search call" not in captured.out
    assert "one-shot-token" not in captured.out
    assert "one-shot-token" not in captured.err


def test_client_handles_200_broker_json_and_writes_ignored_output(
    tmp_path: Path,
) -> None:
    response = {
        "status": "accepted",
        "job_id": "ag96i3d0-official-current-once",
        "sanitized_packet_path": "output/ag96i3d0_packet.json",
    }
    output_relative = f"output/ag96i3d0_test_broker_response_{tmp_path.name}.json"
    output = ROOT / output_relative
    if output.exists():
        output.unlink()
    try:
        with BrokerServer(status=200, response_json=response) as broker:
            result = _run_client(
                "--broker-url",
                broker.url,
                "--job-id",
                "ag96i3d0-official-current-once",
                "--token",
                "one-shot-token",
                "--confirm-live-provider-call",
                "--output",
                output_relative,
            )

        assert result.returncode == 0
        assert "This request may spend one live provider/search call" in result.stdout
        assert "wrote sanitized broker response" in result.stdout
        assert json.loads(output.read_text(encoding="utf-8")) == response
    finally:
        if output.exists():
            output.unlink()


def test_client_handles_400_broker_json_with_nonzero_exit() -> None:
    response = {"error": "unknown_job_id", "job_id": "blocked"}
    with BrokerServer(status=400, response_json=response) as broker:
        result = _run_client(
            "--broker-url",
            broker.url,
            "--job-id",
            "blocked",
            "--token",
            "one-shot-token",
            "--confirm-live-provider-call",
        )

    assert result.returncode == 1
    assert '"error": "unknown_job_id"' in result.stdout


def test_client_handles_403_broker_json_with_nonzero_exit() -> None:
    response = {"error": "invalid_token", "status": "forbidden"}
    with BrokerServer(status=403, response_json=response) as broker:
        result = _run_client(
            "--broker-url",
            broker.url,
            "--job-id",
            "ag96i3d0-official-current-once",
            "--token",
            "one-shot-token",
            "--confirm-live-provider-call",
        )

    assert result.returncode == 1
    assert '"status": "forbidden"' in result.stdout


def test_client_refuses_non_ignored_output_path() -> None:
    result = _run_client(
        "--broker-url",
        "http://127.0.0.1:1/run",
        "--job-id",
        "ag96i3d0-official-current-once",
        "--token",
        "one-shot-token",
        "--confirm-live-provider-call",
        "--output",
        str(ROOT / "docs" / "ag96i3d0_broker_response.json"),
    )

    assert result.returncode == 2
    assert "outside ignored repo output/" in result.stderr


def test_client_refuses_env_output_even_though_gitignored() -> None:
    result = _run_client(
        "--broker-url",
        "http://127.0.0.1:1/run",
        "--job-id",
        "ag96i3d0-official-current-once",
        "--token",
        "one-shot-token",
        "--confirm-live-provider-call",
        "--output",
        str(ROOT / ".env"),
    )

    assert result.returncode == 2
    assert "outside ignored repo output/" in result.stderr


def test_client_refuses_non_output_ignored_private_looking_path() -> None:
    result = _run_client(
        "--broker-url",
        "http://127.0.0.1:1/run",
        "--job-id",
        "ag96i3d0-official-current-once",
        "--token",
        "one-shot-token",
        "--confirm-live-provider-call",
        "--output",
        str(ROOT / "ag96i3d0_token_response.json"),
    )

    assert result.returncode == 2
    assert "outside ignored repo output/" in result.stderr


def test_static_client_imports_no_provider_modules_and_reads_no_env_files() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    imports = _imports(SCRIPT)
    forbidden_imports = {
        "dotenv",
        "requests",
        "openai",
        "core.search_providers",
        "core.pipeline_orchestrator",
        "core.followup_provider_job_live_validation_runtime",
        "core.author_execution_runtime",
    }
    assert imports.isdisjoint(forbidden_imports)
    for forbidden in (
        "BRAVE",
        "TAVILY",
        "LINKUP",
        "EXA",
        "OPENAI",
        "load_dotenv",
        "dotenv_values",
        "brave_reconnaissance",
    ):
        assert forbidden not in source


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _lower_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def _load_client_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "request_live_validation_broker",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
