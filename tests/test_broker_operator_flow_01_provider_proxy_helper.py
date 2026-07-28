from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from scripts import request_provider_proxy_broker as client
from scripts import run_provider_proxy_broker_once as helper
from scripts.provider_execution_contract import (
    BROKER_ENV_FILE_PATH_ENV_VAR,
    BROKER_MAX_REQUESTS_ENV_VAR,
    SEARCH_QUERY_OPERATION,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_provider_proxy_broker_once.py"


class FakeBrokerProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return 0 if self.terminated or self.killed else None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int | None = None) -> int:
        del timeout
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


def _helper_args(env_file: Path, output: str) -> list[str]:
    return [
        "--provider",
        "serper",
        "--operation",
        SEARCH_QUERY_OPERATION,
        "--query",
        "current official example",
        "--max-results",
        "5",
        "--timeout-seconds",
        "30",
        "--retry-cap",
        "0",
        "--cost-ceiling-usd",
        "0.05",
        "--output",
        output,
        "--env-file",
        str(env_file),
        "--confirm-provider-call",
    ]


def test_helper_requires_explicit_provider_call_confirmation(tmp_path: Path) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("opaque", encoding="utf-8")
    args = _helper_args(env_file, "output/missing-confirm.json")
    args.remove("--confirm-provider-call")
    assert helper.main(args) == 2


def test_helper_refuses_output_outside_output(tmp_path: Path) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("opaque", encoding="utf-8")
    assert helper.main(_helper_args(env_file, str(tmp_path / "outside.json"))) == 2


def test_helper_output_preflight_failure_prevents_env_broker_and_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("opaque", encoding="utf-8")
    called: list[str] = []

    def fail_preflight(path: Path) -> Path:
        raise client.OutputHygieneError(
            reason="output_directory_not_writable",
            output_path=path,
            error_type="PermissionError",
        )

    monkeypatch.setattr(client, "prepare_output_path_for_sanitized_write", fail_preflight)
    monkeypatch.setattr(
        helper,
        "normalize_environment_file_path",
        lambda _path: called.append("env") or env_file,
    )
    monkeypatch.setattr(
        helper,
        "start_tracked_broker",
        lambda **_kwargs: called.append("broker"),
    )
    monkeypatch.setattr(
        helper,
        "run_generic_provider_client",
        lambda **_kwargs: called.append("client"),
    )
    assert helper.main(_helper_args(env_file, "output/preflight.json")) == 2
    assert called == []
    assert client.OUTPUT_HYGIENE_DECISION in capsys.readouterr().err


def test_helper_generates_temporary_token_without_printing_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("private bytes", encoding="utf-8")
    process = FakeBrokerProcess()
    captured: dict[str, Any] = {}

    def fake_popen(args: list[str], **kwargs: Any) -> FakeBrokerProcess:
        captured["broker_argv"] = list(args)
        captured["broker_env"] = dict(kwargs["env"])
        return process

    def fake_client(**kwargs: Any) -> int:
        captured["client_argv"] = list(kwargs["client_argv"])
        captured["client_env"] = dict(kwargs["client_env"])
        return 0

    monkeypatch.setattr(helper.secrets, "token_urlsafe", lambda _size: "temporary-token")
    monkeypatch.setattr(helper.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(helper, "wait_for_broker_readiness", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(helper, "run_generic_provider_client", fake_client)
    assert helper.main(_helper_args(env_file, "output/sanitized.json")) == 0

    output = capsys.readouterr()
    assert "temporary-token" not in output.out + output.err
    assert "private bytes" not in output.out + output.err
    assert "temporary-token" not in captured["broker_argv"]
    assert str(env_file) not in captured["broker_argv"]
    assert "temporary-token" not in captured["client_argv"]
    assert str(env_file) not in captured["client_argv"]
    assert captured["broker_env"][client.TOKEN_ENV_VAR] == "temporary-token"
    assert captured["broker_env"][BROKER_ENV_FILE_PATH_ENV_VAR] == str(env_file.resolve())
    assert captured["client_env"][client.TOKEN_ENV_VAR] == "temporary-token"
    assert BROKER_ENV_FILE_PATH_ENV_VAR not in captured["client_env"]
    assert process.terminated is True


def test_helper_passes_generic_provider_request_shape_to_client(tmp_path: Path) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("opaque", encoding="utf-8")
    args = helper._parser().parse_args(_helper_args(env_file, "output/shape.json"))
    argv = helper._client_argv(args)
    assert argv[argv.index("--operation") + 1] == SEARCH_QUERY_OPERATION
    assert argv[argv.index("--retry-cap") + 1] == "0"
    assert "--token" not in argv
    assert "--env-file" not in argv
    assert "--private-broker-path" not in argv
    assert "--python-executable" not in argv


def test_helper_passes_model_status_projection_without_output_retention(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("opaque", encoding="utf-8")
    args = helper._parser().parse_args(
        [
            "--provider",
            "openai",
            "--operation",
            "model.generate",
            "--model",
            "gpt-5.4-2026-03-05",
            "--input-prompt",
            "Return one status object.",
            "--reasoning-effort",
            "medium",
            "--max-output-tokens",
            "128",
            "--maximum-input-tokens",
            "1000",
            "--timeout-seconds",
            "120",
            "--retry-cap",
            "0",
            "--ordinary-input-price-usd-per-million",
            "2.50",
            "--cached-input-price-usd-per-million",
            "0.25",
            "--output-price-usd-per-million",
            "15.00",
            "--cost-ceiling-usd",
            "0.01",
            "--expected-json-status",
            "BROKER_MODEL_OK",
            "--output",
            "output/model-proof.json",
            "--env-file",
            str(env_file),
            "--confirm-provider-call",
        ]
    )
    argv = helper._client_argv(args)
    assert argv[argv.index("--expected-json-status") + 1] == "BROKER_MODEL_OK"
    assert "--env-file" not in argv


def test_helper_loads_only_selected_provider_key_from_explicit_env_file(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "operator.env"
    env_file.write_text("private bytes must not be read\n", encoding="utf-8")
    normalized = helper.normalize_environment_file_path(env_file)
    broker_env = helper.broker_environment(
        token="temporary-token",
        env_file_path=normalized,
        maximum_requests=1,
        process_env={},
    )
    client_env = helper.client_environment(
        token="temporary-token",
        process_env={},
    )
    assert broker_env[BROKER_ENV_FILE_PATH_ENV_VAR] == str(normalized)
    assert broker_env[BROKER_MAX_REQUESTS_ENV_VAR] == "1"
    assert BROKER_ENV_FILE_PATH_ENV_VAR not in client_env
    source = SCRIPT.read_text(encoding="utf-8")
    assert ".read_text(" not in source
    assert ".read_bytes(" not in source
    for credential_name in ("OPENAI_API_KEY", "SERPER_API_KEY", "TAVILY_API_KEY"):
        assert credential_name not in source


def test_helper_rejects_raw_private_fields_through_generic_client(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("opaque", encoding="utf-8")
    args = helper._parser().parse_args(_helper_args(env_file, "output/private.json"))
    argv = helper._client_argv(args)
    rendered = " ".join(argv).casefold()
    for forbidden in ("token", "authorization", "job-id", "profile", "private-broker-path"):
        assert forbidden not in rendered


def test_helper_client_output_is_utf8_without_bom(tmp_path: Path) -> None:
    env = helper.client_environment(token="temporary-token", process_env={})
    assert env["PYTHONIOENCODING"] == "utf-8"
    assert set(env) == {"PYTHONIOENCODING", client.TOKEN_ENV_VAR}
    assert helper.TRACKED_CLIENT_PATH.name == "request_provider_proxy_broker.py"
    assert helper.TRACKED_BROKER_PATH.name == "provider_execution_broker.py"


def test_helper_has_no_task_specific_or_closed_authority_concepts() -> None:
    imported = _imports(SCRIPT)
    source = SCRIPT.read_text(encoding="utf-8")
    assert "core.live_search_validation_invocation_runtime" not in imported
    assert "scripts.provider_execution_broker" not in imported
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
        "OPENAI_API_KEY",
        "SERPER_API_KEY",
        "TAVILY_API_KEY",
    ):
        assert token not in source
