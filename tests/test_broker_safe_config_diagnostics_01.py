"""Safe private-child failure categories; synthetic configuration only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts import run_brokered_command_once as doorman


@pytest.mark.parametrize(("message", "expected"), [
    ("private_session_missing", "private_session_missing"),
    ("environment_file_unavailable", "environment_file_unavailable"),
    ("invalid_environment_assignment", "invalid_environment_assignment"),
    ("invalid_environment_assignment_12", "invalid_environment_assignment"),
    ("invalid_environment_name_3", "invalid_environment_name"),
    ("invalid_environment_value_27", "invalid_environment_value"),
    ("invalid_environment_assignment_", "private_child_configuration_failed"),
    ("invalid_environment_name_3_more", "private_child_configuration_failed"),
    ("invalid_environment_value_27\n", "private_child_configuration_failed"),
    ("invalid_environment_assignment_\u0661", "private_child_configuration_failed"),
    ("environment_file_unavailable_details", "private_child_configuration_failed"),
    ("unknown failure", "private_child_configuration_failed"),
])
def test_private_error_categories_require_exact_known_structure(message: str, expected: str) -> None:
    assert doorman._private_configuration_error_code(doorman.BrokeredCommandError(message)) == expected


def test_private_error_classifier_does_not_stringify_unknown_arguments() -> None:
    class Opaque:
        def __str__(self) -> str:
            raise AssertionError("Private arguments must not be rendered")

    for args in ((), (Opaque(),), ("invalid_environment_name_3", Opaque())):
        assert doorman._private_configuration_error_code(doorman.BrokeredCommandError(*args)) == (
            "private_child_configuration_failed"
        )


@pytest.mark.parametrize("failure", ["missing-file", "unreadable-directory", "missing-session", "missing-nonce", "missing-env-path", "unknown"])
def test_private_configuration_status_and_console_are_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failure: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    private_path = tmp_path / "synthetic.env"
    if failure == "unreadable-directory":
        private_path.mkdir()
    private_state = {
        doorman.PRIVATE_NONCE_ENV_VAR: "synthetic-session",
        doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR: str(private_path),
    }
    if failure == "missing-session":
        private_state.clear()
    elif failure == "missing-nonce":
        private_state.pop(doorman.PRIVATE_NONCE_ENV_VAR)
    elif failure == "missing-env-path":
        private_state.pop(doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR)
    monkeypatch.setattr(doorman.os, "environ", private_state)
    secret = "synthetic-unpublishable-value"  # pragma: allowlist secret
    if failure == "unknown":
        def fail(_path: Path) -> dict[str, str]:
            raise doorman.BrokeredCommandError(f"unknown failure: {secret}; PRIVATE_NAME; line 991")
        monkeypatch.setattr(doorman, "load_private_environment_file", fail)

    def forbid_launch(*_args: object, **_kwargs: object) -> None:
        pytest.fail("A configuration failure must never launch its target")

    monkeypatch.setattr(doorman.subprocess, "Popen", forbid_launch)
    paths = {key: external / name for key, name in (
        ("stdout", "out.txt"), ("stderr", "err.txt"), ("status", "status.json"),
    )}
    result = doorman.main([
        "--private-child", "--repo-root", str(repo),
        "--stdout", str(paths["stdout"]), "--stderr", str(paths["stderr"]),
        "--status", str(paths["status"]), "--timeout-seconds", "1",
        "--", sys.executable, "-c", "pass",
    ])
    expected = (
        "private_session_missing" if failure.startswith("missing-") and failure != "missing-file"
        else "private_child_configuration_failed" if failure == "unknown"
        else "environment_file_unavailable"
    )
    assert result == doorman.CONFIGURATION_EXIT_CODE
    assert json.loads(paths["status"].read_text(encoding="utf-8")) == {
        "schema_version": doorman.STATUS_SCHEMA_VERSION,
        "status": "private_child_configuration_failed", "safe_error_code": expected,
        "target_launch_attempted": False, "target_launch_succeeded": False,
        "target_exit_code": None, "timed_out": False,
        "stdout_sanitized_written": True, "stderr_sanitized_written": True,
    }
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"brokered-command configuration failed: {expected}\n"
    assert paths["stdout"].read_text() == paths["stderr"].read_text() == ""
    for text in (captured.out, captured.err, *(path.read_text(encoding="utf-8") for path in paths.values())):
        assert secret not in text
        assert "PRIVATE_NAME" not in text
        assert "991" not in text
        assert str(private_path) not in text
        assert "Traceback" not in text
