"""Offline coverage for doorman child bootstrap and terminal status handling."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import run_brokered_command_once as doorman


def _write_env(path: Path, text: str = "NORMAL=offline-test\n") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _run(
    *,
    repo_root: Path,
    env_file: Path,
    external_root: Path,
    command: list[str],
    status: Path,
    timeout: float = 10,
) -> int:
    return doorman.main(
        [
            "--repo-root",
            str(repo_root),
            "--env-file",
            str(env_file),
            "--stdout",
            str(external_root / "broker.stdout.txt"),
            "--stderr",
            str(external_root / "broker.stderr.txt"),
            "--status",
            str(status),
            "--timeout-seconds",
            str(timeout),
            "--",
            *command,
        ]
    )


def test_target_launch_failure_has_controlled_status_and_safe_outputs(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    status_path = external_root / "broker.status.json"
    missing_target = tmp_path / "not-installed-target.exe"

    result = _run(
        repo_root=repo_root,
        env_file=_write_env(tmp_path / "synthetic.env"),
        external_root=external_root,
        command=[str(missing_target)],
        status=status_path,
    )

    assert result == doorman.TARGET_LAUNCH_FAILURE_EXIT_CODE
    assert json.loads(status_path.read_text(encoding="utf-8")) == {
        "schema_version": doorman.STATUS_SCHEMA_VERSION,
        "target_launch_attempted": True,
        "target_launch_succeeded": False,
        "target_exit_code": None,
        "timed_out": False,
        "stdout_sanitized_written": True,
        "stderr_sanitized_written": True,
        "status": "target_launch_failed",
        "safe_error_code": "target_executable_unavailable",
    }
    assert (external_root / "broker.stdout.txt").read_text() == ""
    assert (external_root / "broker.stderr.txt").read_text() == ""


def test_timeout_has_structural_status_without_raw_material(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    status_path = external_root / "broker.status.json"

    result = _run(
        repo_root=repo_root,
        env_file=_write_env(tmp_path / "synthetic.env"),
        external_root=external_root,
        command=[sys.executable, "-c", "import time; time.sleep(2)"],
        status=status_path,
        timeout=0.1,
    )

    assert result == doorman.TIMEOUT_EXIT_CODE
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["schema_version"] == doorman.STATUS_SCHEMA_VERSION
    assert status["target_launch_attempted"] is True
    assert status["target_launch_succeeded"] is True
    assert status["timed_out"] is True
    assert status["status"] == "target_timeout"
    assert status["stdout_sanitized_written"] is True
    assert status["stderr_sanitized_written"] is True


def test_private_child_configuration_failure_has_safe_status(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    status_path = external_root / "broker.status.json"

    result = _run(
        repo_root=repo_root,
        env_file=_write_env(tmp_path / "synthetic.env", "not dotenv syntax\n"),
        external_root=external_root,
        command=[sys.executable, "-c", "pass"],
        status=status_path,
    )

    assert result == doorman.CONFIGURATION_EXIT_CODE
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "private_child_configuration_failed"
    assert status["safe_error_code"] == "private_child_configuration_failed"
    assert status["target_launch_attempted"] is False
    assert status["target_launch_succeeded"] is False
