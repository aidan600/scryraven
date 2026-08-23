"""Offline proof for broker status and bounded-target bootstrap totality."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ag_live_bound_01_target_bootstrap as bootstrap
from scripts import run_brokered_command_once as doorman

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "ag_live_bound_01_target_bootstrap.py"
Q1_QUERY = (
    "According to the official Python 3 documentation, what are the default "
    "values for rel_tol and abs_tol in math.isclose()?"
)


def _write_synthetic_env(path: Path, text: str = "NORMAL=offline-test\n") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _run_broker(
    *,
    repo_root: Path,
    env_file: Path,
    external_root: Path,
    command: list[str],
    status: Path,
    timeout: float = 10,
    target_current_python: bool = False,
) -> int:
    stdout = external_root / "broker.stdout.txt"
    stderr = external_root / "broker.stderr.txt"
    options = [
        "--repo-root",
        str(repo_root),
        "--env-file",
        str(env_file),
        "--stdout",
        str(stdout),
        "--stderr",
        str(stderr),
        "--status",
        str(status),
        "--timeout-seconds",
        str(timeout),
    ]
    if target_current_python:
        options.append("--target-current-python")
    return doorman.main([*options, "--", *command])


def _status(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_target_launch_oserror_has_controlled_status_and_safe_outputs(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    env_file = _write_synthetic_env(tmp_path / "synthetic.env")
    status_path = external_root / "broker.status.json"
    missing_target = tmp_path / "not-installed-target.exe"

    result = _run_broker(
        repo_root=repo_root,
        env_file=env_file,
        external_root=external_root,
        command=[str(missing_target)],
        status=status_path,
    )

    assert result == doorman.TARGET_LAUNCH_FAILURE_EXIT_CODE
    status = _status(status_path)
    assert status == {
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
    assert not (external_root / "product.sanitized.json").exists()


def test_current_python_target_uses_private_child_interpreter_and_completes(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    env_file = _write_synthetic_env(tmp_path / "synthetic.env")
    status_path = external_root / "broker.status.json"
    target = tmp_path / "target.py"
    target.write_text(
        "import json, sys\nprint(json.dumps({'executable': sys.executable}))\n",
        encoding="utf-8",
    )

    result = _run_broker(
        repo_root=repo_root,
        env_file=env_file,
        external_root=external_root,
        command=[str(target)],
        status=status_path,
        target_current_python=True,
    )

    assert result == 0
    assert _status(status_path) == {
        "schema_version": doorman.STATUS_SCHEMA_VERSION,
        "target_launch_attempted": True,
        "target_launch_succeeded": True,
        "target_exit_code": 0,
        "timed_out": False,
        "stdout_sanitized_written": True,
        "stderr_sanitized_written": True,
        "status": "target_completed",
        "safe_error_code": None,
    }
    payload = json.loads((external_root / "broker.stdout.txt").read_text())
    assert payload["executable"] == sys.executable


def test_broker_bootstrap_q1_dry_run_is_end_to_end_and_non_live(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    env_file = _write_synthetic_env(tmp_path / "synthetic.env")
    status_path = external_root / "broker.status.json"
    packet_path = external_root / "product.sanitized.json"
    command = [
        str(BOOTSTRAP),
        "--profile",
        "AG-LIVE-SMOKE",
        "--query",
        Q1_QUERY,
        "--mode",
        "Balanced",
        "--include-domains",
        "docs.python.org",
        "--output",
        str(packet_path),
        "--external-output-root",
        str(external_root),
        "--max-scryraven-runs",
        "1",
        "--max-retries",
        "0",
    ]

    result = _run_broker(
        repo_root=repo_root,
        env_file=env_file,
        external_root=external_root,
        command=command,
        status=status_path,
        target_current_python=True,
    )

    assert result == 0
    assert _status(status_path)["status"] == "target_completed"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["dry_run"] is True
    assert packet["confirm_live_product_run"] is False
    assert packet["planned_live_dispatch"] is False
    assert packet["validation_profile"]["name"] == "AG-LIVE-SMOKE"


def test_private_child_configuration_failure_has_safe_status(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    env_file = _write_synthetic_env(tmp_path / "synthetic.env", "not dotenv syntax\n")
    status_path = external_root / "broker.status.json"

    result = _run_broker(
        repo_root=repo_root,
        env_file=env_file,
        external_root=external_root,
        command=[sys.executable, "-c", "pass"],
        status=status_path,
    )

    assert result == doorman.CONFIGURATION_EXIT_CODE
    status = _status(status_path)
    assert status["status"] == "private_child_configuration_failed"
    assert status["safe_error_code"] == "private_child_configuration_failed"
    assert status["target_launch_attempted"] is False
    assert status["target_launch_succeeded"] is False


def test_bootstrap_import_failure_writes_minimal_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    packet_path = external_root / "product.sanitized.json"
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        bootstrap.importlib,
        "import_module",
        lambda _name: (_ for _ in ()).throw(ModuleNotFoundError("not serialized")),
    )

    result = bootstrap.main(
        [
            "--output",
            str(packet_path),
            "--external-output-root",
            str(external_root),
        ]
    )

    assert result == bootstrap.BOOTSTRAP_FAILURE_EXIT_CODE
    assert json.loads(packet_path.read_text(encoding="utf-8")) == {
        "schema_version": bootstrap.BOOTSTRAP_SCHEMA_VERSION,
        "classification": "runner_bootstrap_failure",
        "safe_phase": "runner_import",
        "safe_error_type": "ModuleNotFoundError",
        "runner_exit_code": None,
        "product_result_available": False,
        "raw_private_material_retained": False,
    }


def test_broker_to_bootstrap_import_failure_has_terminal_packet(
    tmp_path: Path,
) -> None:
    external_root = tmp_path / "external"
    external_root.mkdir()
    env_file = _write_synthetic_env(tmp_path / "synthetic.env")
    status_path = external_root / "broker.status.json"
    packet_path = external_root / "product.sanitized.json"
    target = tmp_path / "import_failure_target.py"
    target.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from scripts import ag_live_bound_01_target_bootstrap as bootstrap\n"
        "def fail(_name):\n"
        "    raise ModuleNotFoundError('not serialized')\n"
        "bootstrap.importlib.import_module = fail\n"
        "raise SystemExit(bootstrap.main(sys.argv[1:]))\n",
        encoding="utf-8",
    )

    result = _run_broker(
        repo_root=ROOT,
        env_file=env_file,
        external_root=external_root,
        command=[
            str(target),
            "--output",
            str(packet_path),
            "--external-output-root",
            str(external_root),
        ],
        status=status_path,
        target_current_python=True,
    )

    assert result == bootstrap.BOOTSTRAP_FAILURE_EXIT_CODE
    assert _status(status_path)["status"] == "target_completed"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["classification"] == "runner_bootstrap_failure"
    assert packet["safe_phase"] == "runner_import"
    assert packet["product_result_available"] is False


def test_bootstrap_runner_nonzero_without_packet_gets_safe_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    external_root.mkdir()
    packet_path = external_root / "product.sanitized.json"
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        bootstrap.importlib,
        "import_module",
        lambda _name: SimpleNamespace(main=lambda _argv: 17),
    )

    result = bootstrap.main(
        [
            "--output",
            str(packet_path),
            "--external-output-root",
            str(external_root),
        ]
    )

    assert result == 17
    assert json.loads(packet_path.read_text(encoding="utf-8")) == {
        "schema_version": bootstrap.BOOTSTRAP_SCHEMA_VERSION,
        "classification": "runner_exited_without_packet",
        "safe_phase": "runner_return",
        "safe_error_type": None,
        "runner_exit_code": 17,
        "product_result_available": False,
        "raw_private_material_retained": False,
    }


def test_broker_to_bootstrap_nonzero_runner_has_terminal_packet(
    tmp_path: Path,
) -> None:
    external_root = tmp_path / "external"
    external_root.mkdir()
    env_file = _write_synthetic_env(tmp_path / "synthetic.env")
    status_path = external_root / "broker.status.json"
    packet_path = external_root / "product.sanitized.json"
    target = tmp_path / "nonzero_runner_target.py"
    target.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from types import SimpleNamespace\n"
        "from scripts import ag_live_bound_01_target_bootstrap as bootstrap\n"
        "bootstrap.importlib.import_module = lambda _name: "
        "SimpleNamespace(main=lambda _argv: 17)\n"
        "raise SystemExit(bootstrap.main(sys.argv[1:]))\n",
        encoding="utf-8",
    )

    result = _run_broker(
        repo_root=ROOT,
        env_file=env_file,
        external_root=external_root,
        command=[
            str(target),
            "--output",
            str(packet_path),
            "--external-output-root",
            str(external_root),
        ],
        status=status_path,
        target_current_python=True,
    )

    assert result == 17
    assert _status(status_path)["status"] == "target_completed"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["classification"] == "runner_exited_without_packet"
    assert packet["runner_exit_code"] == 17
    assert packet["product_result_available"] is False
