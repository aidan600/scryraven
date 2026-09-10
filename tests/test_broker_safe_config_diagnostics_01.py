"""Safe private-child failure categories; synthetic configuration only."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from scripts import run_brokered_command_once as doorman


@pytest.mark.parametrize(("message", "expected"), [
    ("private_session_missing", "private_session_missing"),
    ("environment_file_unavailable", "environment_file_unavailable"),
    ("environment_file_read_error", "environment_file_read_error"),
    ("environment_file_decode_error", "environment_file_decode_error"),
    ("environment_file_not_found_at_read", "environment_file_not_found_at_read"),
    ("environment_file_permission_denied", "environment_file_permission_denied"),
    ("environment_file_sharing_violation", "environment_file_sharing_violation"),
    ("environment_file_other_read_error", "environment_file_other_read_error"),
    ("invalid_environment_assignment", "invalid_environment_assignment"),
    ("invalid_environment_assignment_12", "invalid_environment_assignment"),
    ("invalid_environment_name_3", "invalid_environment_name"),
    ("invalid_environment_value_27", "invalid_environment_value"),
    ("invalid_environment_assignment_", "private_child_configuration_failed"),
    ("invalid_environment_name_3_more", "private_child_configuration_failed"),
    ("invalid_environment_value_27\n", "private_child_configuration_failed"),
    ("invalid_environment_assignment_\u0661", "private_child_configuration_failed"),
    ("environment_file_unavailable_details", "private_child_configuration_failed"),
    ("environment_file_read_error_73", "private_child_configuration_failed"),
    ("environment_file_decode_error_details", "private_child_configuration_failed"),
    ("environment_file_not_found_at_read_private.env", "private_child_configuration_failed"),
    ("environment_file_permission_denied_5", "private_child_configuration_failed"),
    ("environment_file_sharing_violation_32", "private_child_configuration_failed"),
    ("environment_file_other_read_error_details", "private_child_configuration_failed"),
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


@pytest.mark.parametrize("failure", ["missing-file", "unreadable-directory", "missing-session", "missing-nonce", "missing-env-path", "legacy-unavailable", "legacy-read-error", "unknown"])
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
    if failure in {"legacy-unavailable", "legacy-read-error", "unknown"}:
        def fail(_path: Path) -> dict[str, str]:
            if failure == "legacy-unavailable":
                raise doorman.BrokeredCommandError("environment_file_unavailable")
            if failure == "legacy-read-error":
                raise doorman.BrokeredCommandError("environment_file_read_error")
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
        else "environment_file_unavailable" if failure == "legacy-unavailable"
        else "environment_file_read_error" if failure == "legacy-read-error"
        else "environment_file_not_found_at_read" if failure == "missing-file"
        else "environment_file_permission_denied" if os.name == "nt"
        else "environment_file_other_read_error"
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


@pytest.mark.parametrize(("failure", "expected"), [
    ("decode", "environment_file_decode_error"),
    ("read", "environment_file_other_read_error"),
    ("not-found", "environment_file_not_found_at_read"),
    ("permission", "environment_file_permission_denied"),
    ("sharing", "environment_file_sharing_violation"),
    ("lock", "environment_file_sharing_violation"),
    ("permission-with-other-winerror", "environment_file_permission_denied"),
])
def test_private_environment_input_failure_has_only_fixed_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    failure: str, expected: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    private_path = tmp_path / "private-input-only-filename.env"
    private_name = "SYNTHETIC_PRIVATE_TOKEN"
    private_value = "synthetic-unpublishable-input-value"  # pragma: allowlist secret
    contents = f"{private_name}={private_value}\n".encode("utf-8")
    private_path.write_bytes(contents + (b"\xff\xfe\n" if failure == "decode" else b""))
    error_type = (
        FileNotFoundError if failure == "not-found"
        else PermissionError if failure in {"permission", "sharing", "lock", "permission-with-other-winerror"}
        else OSError
    )
    read_error = error_type(73, f"synthetic-read-detail {private_name}={private_value}", str(private_path))
    if failure in {"sharing", "lock", "permission-with-other-winerror"}:
        read_error.winerror = {"sharing": 32, "lock": 33, "permission-with-other-winerror": 5}[failure]
    if failure != "decode":
        original_read_text = Path.read_text

        def fail_private_read(path: Path, *args: object, **kwargs: object) -> str:
            if path == private_path:
                assert kwargs == {"encoding": "utf-8-sig"}
                raise read_error
            return original_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fail_private_read)
    monkeypatch.setattr(doorman.os, "environ", {
        doorman.PRIVATE_NONCE_ENV_VAR: "synthetic-session",
        doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR: str(private_path),
    })

    def forbid_launch(*_args: object, **_kwargs: object) -> None:
        pytest.fail("An environment input failure must never launch its target")

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
    assert result == doorman.CONFIGURATION_EXIT_CODE == 2
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
        for forbidden in (
            private_name, private_value, private_path.name, str(private_path),
            str(read_error), "synthetic-read-detail", "73", str(len(contents)),
            "OSError", "FileNotFoundError", "PermissionError", "UnicodeDecodeError", "Traceback",
            "32", "33", "winerror", "errno", "utf-8", "position", "offset",
            "0xff", "0xfe", "\\xff", "\\xfe", "\ufffd", "invalid start byte",
        ):
            assert forbidden not in text


@pytest.mark.parametrize("decode_failure", [False, True], ids=["valid", "decode-error"])
def test_synthetic_environment_input_through_parent_and_private_child(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], decode_failure: bool,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    private_path = tmp_path / "parent-input-only-filename.env"
    private_name = "SYNTHETIC_PRIVATE_TOKEN"
    private_value = "synthetic-parent-input-value"  # pragma: allowlist secret
    contents = f"export {private_name}='{private_value}'\n".encode("utf-8-sig")
    private_path.write_bytes(contents + (b"\xff\n" if decode_failure else b""))
    paths = {key: external / name for key, name in (
        ("stdout", "out.txt"), ("stderr", "err.txt"), ("status", "status.json"),
    )}
    result = doorman.main([
        "--repo-root", str(repo), "--env-file", str(private_path),
        "--stdout", str(paths["stdout"]), "--stderr", str(paths["stderr"]),
        "--status", str(paths["status"]), "--timeout-seconds", "10",
        "--", sys.executable, "-c", (
            f"import os; assert os.environ[{private_name!r}] == {private_value!r}; "
            "print('BROKER_SYNTHETIC_OK')"
        ),
    ])
    assert result == (2 if decode_failure else 0)
    assert json.loads(paths["status"].read_text(encoding="utf-8")) == {
        "schema_version": doorman.STATUS_SCHEMA_VERSION,
        "status": "private_child_configuration_failed" if decode_failure else "target_completed",
        "safe_error_code": "environment_file_decode_error" if decode_failure else None,
        "target_launch_attempted": not decode_failure, "target_launch_succeeded": not decode_failure,
        "target_exit_code": None if decode_failure else 0, "timed_out": False,
        "stdout_sanitized_written": True, "stderr_sanitized_written": True,
    }
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert paths["stdout"].read_text() == ("" if decode_failure else "BROKER_SYNTHETIC_OK\n")
    assert paths["stderr"].read_text() == ""
    for text in (captured.out, captured.err, *(path.read_text(encoding="utf-8") for path in paths.values())):
        for forbidden in (
            private_name, private_value, private_path.name, str(private_path),
            "UnicodeDecodeError", "Traceback", "utf-8", "position", "offset",
            str(len(contents) - 3), "0xff", "\\xff", "\ufffd", "invalid start byte",
        ):
            assert forbidden not in text
