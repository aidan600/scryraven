from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import request_live_validation_broker as retired

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "request_live_validation_broker.py"


def _run_client(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_client_refuses_without_token() -> None:
    assert retired.main([]) == 2


def test_client_refuses_without_live_spend_confirmation() -> None:
    assert retired.main(["--confirm-live-provider-call"]) == 2


def test_confirm_flag_help_names_profile_bounded_budget() -> None:
    result = _run_client("--help")
    assert result.returncode == 2
    assert "retired_validation_broker_path" in result.stderr
    assert "validation profile" not in result.stderr.casefold()


def test_client_constructs_expected_post_body_and_token_header_only() -> None:
    source = _source()
    assert "urlopen" not in source
    assert "Request(" not in source
    assert "TOKEN_HEADER" not in source
    assert "_build_profile_request_payload" not in source


def test_client_warning_uses_selected_profile_budget() -> None:
    source = _source()
    assert "LIVE_SPEND_WARNING" not in source
    assert "BUDGET_SUMMARY_FIELDS" not in source
    assert "cost" not in retired.RETIREMENT_MESSAGE.casefold()


def test_client_refuses_unknown_profile_before_contacting_broker() -> None:
    result = _run_client("--profile", "unknown", "--job-id", "anything")
    assert result.returncode == 2
    assert "retired_validation_broker_path" in result.stderr
    assert "unknown" not in result.stderr
    assert "anything" not in result.stderr


def test_client_can_read_token_from_environment_without_printing_it() -> None:
    env = dict(os.environ)
    env["SCRYRAVEN_BROKER_SESSION_TOKEN"] = "temporary-secret"
    result = _run_client(env=env)
    assert result.returncode == 2
    assert "temporary-secret" not in result.stdout + result.stderr


def test_default_and_localhost_broker_urls_are_accepted() -> None:
    for url in ("http://127.0.0.1:8765/run", "http://localhost:8765/run"):
        result = _run_client("--broker-url", url)
        assert result.returncode == 2
        assert url not in result.stdout + result.stderr


def test_client_refuses_https_non_local_broker_url_before_warning() -> None:
    result = _run_client("--broker-url", "https://example.com/run")
    assert result.returncode == 2
    assert "example.com" not in result.stderr
    assert "retired_validation_broker_path" in result.stderr


def test_client_refuses_public_provider_broker_url_without_contacting_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(subprocess, "run", forbidden)
    assert retired.main(["--broker-url", "https://provider.example/run"]) == 2
    assert called is False


def test_client_handles_200_broker_json_and_writes_ignored_output(
    tmp_path: Path,
) -> None:
    target = tmp_path / "would-have-been-written.json"
    assert retired.main(["--output", str(target)]) == 2
    assert not target.exists()


def test_client_handles_400_broker_json_with_nonzero_exit() -> None:
    assert retired.main(["--job-id", "blocked"]) == 2
    assert "400" not in _source()


def test_client_handles_403_broker_json_with_nonzero_exit() -> None:
    assert retired.main(["--token", "blocked"]) == 2
    assert "403" not in _source()


def test_client_refuses_non_ignored_output_path(tmp_path: Path) -> None:
    target = tmp_path / "docs" / "blocked.json"
    assert retired.main(["--output", str(target)]) == 2
    assert not target.exists()


def test_client_refuses_env_output_even_though_gitignored(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    assert retired.main(["--output", str(target)]) == 2
    assert not target.exists()


def test_client_refuses_non_output_ignored_private_looking_path(tmp_path: Path) -> None:
    target = tmp_path / "private-token-response.json"
    assert retired.main(["--output", str(target)]) == 2
    assert not target.exists()


def test_static_client_imports_no_provider_modules_and_reads_no_env_files() -> None:
    tree = ast.parse(_source())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports == {"__future__", "sys"}
    source = _source()
    for forbidden in (
        "urllib",
        "subprocess",
        "core.validation_profiles",
        "get_validation_profile",
        "job_id",
        "profile_name",
        "open(",
        "read_text",
        "write_text",
        "provider_execution_broker",
    ):
        assert forbidden not in source
