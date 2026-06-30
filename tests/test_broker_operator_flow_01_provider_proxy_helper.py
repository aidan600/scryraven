from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from scripts import request_provider_proxy_broker as client
from scripts import run_provider_proxy_broker_once as helper

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_provider_proxy_broker_once.py"


class FakeBrokerProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False
        self.waits = 0

    def poll(self) -> int | None:
        return None if not self.terminated and not self.killed else 0

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int | None = None) -> int:
        self.waits += 1
        return 0

    def kill(self) -> None:
        self.killed = True


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _output_path(name: str) -> Path:
    return ROOT / "output" / name


def _sample_response(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "title": "Example Result",
        "url": "https://example.gov/current",
        "domain": "example.gov",
        "snippet": "Sanitized result snippet.",
        "rank": 1,
        "call_index": 1,
    }
    if extra:
        result.update(extra)
    return {
        "results": [result],
        "raw_provider_payload_retained": False,
        "raw_search_response_retained": False,
    }


def test_helper_requires_explicit_provider_call_confirmation() -> None:
    assert helper.main(
        [
            "--provider",
            "serper",
            "--query",
            "current official example",
            "--output",
            "output/broker_operator_missing_confirm.json",
        ]
    ) == 2


def test_helper_refuses_output_outside_output() -> None:
    assert helper.main(
        [
            "--provider",
            "serper",
            "--query",
            "current official example",
            "--output",
            str(ROOT / "not-output" / "broker_operator_response.json"),
            "--confirm-provider-call",
        ]
    ) == 2


def test_helper_output_preflight_failure_prevents_env_broker_and_client(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, Any] = {}

    def fake_preflight(path: Path) -> Path:
        captured["preflight_path"] = path
        raise client.OutputHygieneError(
            reason="output_directory_not_writable",
            output_path=path,
            error_type="PermissionError",
        )

    def fail_after_preflight(*_args: Any, **_kwargs: Any) -> Any:
        captured["called_after_preflight"] = True
        raise AssertionError("output preflight failure must stop before live setup")

    monkeypatch.setattr(client, "prepare_output_path_for_sanitized_write", fake_preflight)
    monkeypatch.setattr(helper, "generate_temporary_broker_token", fail_after_preflight)
    monkeypatch.setattr(helper, "broker_environment", fail_after_preflight)
    monkeypatch.setattr(helper, "start_private_broker", fail_after_preflight)
    monkeypatch.setattr(helper, "run_generic_provider_client", fail_after_preflight)

    rc = helper.main(
        [
            "--provider",
            "serper",
            "--operation",
            "search",
            "--query",
            "current official example",
            "--max-results",
            "5",
            "--output",
            "output/broker_operator_preflight_blocks.json",
            "--private-broker-path",
            str(ROOT / "private-does-not-run.py"),
            "--env-file",
            str(ROOT / ".env"),
            "--confirm-provider-call",
        ]
    )

    err = capsys.readouterr().err
    assert rc == 2
    assert "preflight_path" in captured
    assert "called_after_preflight" not in captured
    assert client.OUTPUT_HYGIENE_DECISION in err
    assert "output_directory_not_writable" in err
    assert "temporary-token" not in err
    assert "serper-secret" not in err
    assert ".env" not in err
    assert "api_key" not in err.casefold()
    assert "raw_provider_payload\":" not in err
    assert "raw_search_response\":" not in err
    assert "full_trace" not in err


def test_helper_generates_temporary_token_without_printing_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    broker_file = tmp_path / "scryraven_live_broker.py"
    broker_file.write_text("print('not executed')\n", encoding="utf-8")
    fake_process = FakeBrokerProcess()
    captured: dict[str, Any] = {}

    def fake_popen(args: list[str], **kwargs: Any) -> FakeBrokerProcess:
        captured["args"] = args
        captured["env"] = dict(kwargs["env"])
        captured["stdout"] = kwargs["stdout"]
        captured["stderr"] = kwargs["stderr"]
        return fake_process

    def fake_client(**kwargs: Any) -> int:
        captured["client"] = kwargs
        return 0

    monkeypatch.setattr(helper.secrets, "token_urlsafe", lambda _size: "temporary-token")
    monkeypatch.setattr(helper.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(helper, "run_generic_provider_client", fake_client)
    monkeypatch.setattr(helper.time, "sleep", lambda _seconds: None)
    monkeypatch.setenv(helper.SERPER_KEY_ENV_VAR, "serper-secret")

    rc = helper.main(
        [
            "--provider",
            "serper",
            "--operation",
            "search",
            "--query",
            "current official example",
            "--max-results",
            "5",
            "--output",
            "output/broker_operator_sanitized.json",
            "--private-broker-path",
            str(broker_file),
            "--confirm-provider-call",
        ]
    )

    out = capsys.readouterr()
    assert rc == 0
    assert "temporary-token" not in out.out
    assert "temporary-token" not in out.err
    assert "serper-secret" not in out.out
    assert "serper-secret" not in out.err
    assert captured["env"][client.TOKEN_ENV_VAR] == "temporary-token"
    assert captured["env"][helper.SERPER_KEY_ENV_VAR] == "serper-secret"
    assert captured["client"]["token"] == "temporary-token"
    assert fake_process.terminated is True


def test_helper_passes_generic_provider_request_shape_to_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_client_main(argv: list[str]) -> int:
        captured["argv"] = list(argv)
        return 0

    monkeypatch.setattr(client, "main", fake_client_main)

    rc = helper.run_generic_provider_client(
        broker_url="http://127.0.0.1:8765/run",
        provider="serper",
        operation="search",
        query="current official example",
        max_results=5,
        output="output/broker_operator_client_shape.json",
        token="temporary-token",
    )

    assert rc == 0
    assert captured["argv"] == [
        "--broker-url",
        "http://127.0.0.1:8765/run",
        "--provider",
        "serper",
        "--operation",
        "search",
        "--query",
        "current official example",
        "--max-results",
        "5",
        "--output",
        "output/broker_operator_client_shape.json",
        "--token",
        "temporary-token",
        "--confirm-provider-call",
    ]


def test_helper_loads_only_needed_key_from_explicit_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / "operator.env"
    env_file.write_text(
        "\ufeff# local only\n"
        f"{helper.SERPER_KEY_ENV_VAR}=example-provider-value\n"
        f"{client.TOKEN_ENV_VAR}=ignored-token\n"
        "UNRELATED=value\n",
        encoding="utf-8",
    )

    values = helper.load_env_file_values(env_file)
    env = helper.broker_environment(
        provider="serper",
        token="temporary-token",
        env_file_paths=[str(env_file)],
        process_env={},
    )

    assert values == {helper.SERPER_KEY_ENV_VAR: "example-provider-value"}
    assert env[client.TOKEN_ENV_VAR] == "temporary-token"
    assert env[helper.SERPER_KEY_ENV_VAR] == "example-provider-value"
    assert "UNRELATED" not in env


def test_helper_rejects_raw_private_fields_through_generic_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(
        broker_url: str,
        token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        return 200, _sample_response({"raw_search_response": "private"})

    monkeypatch.setattr(client, "_post_broker_json", fake_post)

    assert helper.run_generic_provider_client(
        broker_url="http://127.0.0.1:8765/run",
        provider="serper",
        operation="search",
        query="current official example",
        max_results=5,
        output=str(_output_path("broker_operator_rejects_raw.json")),
        token="temporary-token",
    ) == 2


def test_helper_client_output_is_utf8_without_bom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _output_path("broker_operator_utf8_without_bom.json")

    def fake_post(
        broker_url: str,
        token: str,
        payload: Mapping[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        return 200, _sample_response()

    monkeypatch.setattr(client, "_post_broker_json", fake_post)

    rc = helper.run_generic_provider_client(
        broker_url="http://127.0.0.1:8765/run",
        provider="serper",
        operation="search",
        query="current official example",
        max_results=5,
        output=str(output),
        token="temporary-token",
    )

    assert rc == 0
    raw = output.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    decoded = json.loads(raw.decode("utf-8"))
    assert decoded["raw_provider_payload_retained"] is False
    assert decoded["raw_search_response_retained"] is False


def test_helper_has_no_task_specific_or_closed_authority_concepts() -> None:
    imported = _imports(SCRIPT)
    source = SCRIPT.read_text(encoding="utf-8")

    assert "core.live_search_validation_invocation_runtime" not in imported
    assert "scripts.ag_live_xaxis_validation_01a_live_run_01_harness" not in imported
    for token in (
        "job_id",
        "validation_profile",
        "RunKernel",
        "EvidenceLedger",
        "citation",
        "Sufficiency",
        "FAP",
        "Author",
        "ALLOWLISTED_JOBS",
    ):
        assert token not in source
