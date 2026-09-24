"""Offline checks for the development-only PowerShell forensic run scripts."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

from scryraven.model import ModelConfig

REPOSITORY = Path(__file__).resolve().parents[1]
LAUNCHER = REPOSITORY / "scripts" / "forensic-reading-room.ps1"
CLEANUP = REPOSITORY / "scripts" / "clean-forensic-run.ps1"
FORENSIC_ROOT = Path("C:/tmp/scryraven-forensic")


def _powershell() -> str:
    if os.name != "nt":
        pytest.skip("The forensic launcher is Windows-specific")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        pytest.skip("PowerShell is unavailable")
    return shell


def _prepare(*, port: int | None = None) -> tuple[Path, dict[str, object], str]:
    command = [_powershell(), "-NoProfile", "-File", str(LAUNCHER), "-PrepareOnly"]
    if port is not None:
        command.extend(["-Port", str(port)])
    result = subprocess.run(
        command, cwd=REPOSITORY, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.search(r"^Run directory: (.+)$", result.stdout, re.MULTILINE)
    assert match is not None, result.stdout
    run_directory = Path(match.group(1).strip())
    manifest = json.loads((run_directory / "manifest.json").read_text(encoding="utf-8"))
    return run_directory, manifest, result.stdout


def _cleanup(run_directory: str, clipboard_path: Path) -> subprocess.CompletedProcess[str]:
    # Intercept Set-Clipboard so this test proves the written review summary
    # without changing the developer's actual Windows clipboard.
    environment = os.environ.copy()
    environment.update({
        "SR_CLEANUP_SCRIPT": str(CLEANUP),
        "SR_RUN_DIRECTORY": run_directory,
        "SR_TEST_CLIPBOARD": str(clipboard_path),
    })
    wrapper = (
        "function Set-Clipboard { param([string]$Value) "
        "[System.IO.File]::WriteAllText($env:SR_TEST_CLIPBOARD, $Value) }; "
        "& $env:SR_CLEANUP_SCRIPT -RunDirectory $env:SR_RUN_DIRECTORY"
    )
    return subprocess.run(
        [_powershell(), "-NoProfile", "-Command", wrapper],
        cwd=REPOSITORY, env=environment, capture_output=True, text=True,
        encoding="utf-8", check=False,
    )


def test_launcher_has_exact_reading_room_command_and_no_credential_loader() -> None:
    script = LAUNCHER.read_text(encoding="utf-8")
    for flag in ("--database", "--dogfood-log", "--forensic-log", "--port"):
        assert f"'{flag}'" in script
    assert "& $pythonExecutable @readingRoomArgs" in script
    assert "'scryraven.reading_room'" in script
    assert "Get-Content .env" not in script
    assert "ReadAllText" not in script


def test_prepare_unique_run_manifest_port_and_exact_command(tmp_path: Path) -> None:
    run_a, manifest_a, output_a = _prepare()
    run_b, manifest_b, output_b = _prepare(port=7442)
    try:
        assert run_a != run_b
        assert run_a.parent == FORENSIC_ROOT
        assert run_b.parent == FORENSIC_ROOT
        assert manifest_a["forensic_mode"] is True
        assert manifest_a["repository_path"] == str(REPOSITORY)
        assert re.fullmatch(r"[0-9a-f]{40}", str(manifest_a["git_sha"]))
        assert manifest_a["git_branch"]
        assert manifest_a["run_directory"] == str(run_a)
        assert manifest_a["port"] == 7332
        assert manifest_b["port"] == 7442
        assert manifest_a["model_profile"] == asdict(ModelConfig())
        python_executable = REPOSITORY / ".venv" / "Scripts" / "python.exe"
        if python_executable.exists():
            assert f'Command: & "{python_executable}" -m scryraven.reading_room' in output_a
        for run, manifest, output, port in (
            (run_a, manifest_a, output_a, 7332),
            (run_b, manifest_b, output_b, 7442),
        ):
            database = run / "sessions.sqlite3"
            dogfood = run / "turns.jsonl"
            forensic = run / "observer.jsonl"
            assert manifest["session_database_path"] == str(database)
            assert manifest["dogfood_log_path"] == str(dogfood)
            assert manifest["forensic_observer_log_path"] == str(forensic)
            assert manifest["launch_timestamp_utc"]
            assert "FORENSIC DOGFOOD MODE" in output
            assert "Source text and diagnostic observer events are being saved locally." in output
            assert f"Reading Room URL: http://127.0.0.1:{port}" in output
            assert f'--database "{database}"' in output
            assert f'--dogfood-log "{dogfood}"' in output
            assert f'--forensic-log "{forensic}"' in output
            assert f"--port {port}" in output
            assert "Prepared only; Reading Room was not started." in output
    finally:
        for run in (run_a, run_b):
            if run.is_dir():
                result = _cleanup(str(run), tmp_path / f"{run.name}-clipboard.txt")
                assert result.returncode == 0, result.stdout + result.stderr


def test_prepare_records_detached_head_without_a_branch_name(tmp_path: Path) -> None:
    # Pull-request CI checks out a detached commit. Shadow only the branch
    # lookup; the revision still comes from the real repository.
    environment = os.environ.copy()
    environment["SR_LAUNCHER_SCRIPT"] = str(LAUNCHER)
    wrapper = (
        "function git { if ($args -contains 'branch') { $global:LASTEXITCODE = 0; return }; "
        "& git.exe @args }; & $env:SR_LAUNCHER_SCRIPT -PrepareOnly"
    )
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-Command", wrapper],
        cwd=REPOSITORY, env=environment, capture_output=True, text=True,
        encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.search(r"^Run directory: (.+)$", result.stdout, re.MULTILINE)
    assert match is not None, result.stdout
    run = Path(match.group(1).strip())
    try:
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["git_branch"] == "(detached HEAD)"
        assert re.fullmatch(r"[0-9a-f]{40}", manifest["git_sha"])
    finally:
        if run.is_dir():
            cleaned = _cleanup(str(run), tmp_path / "detached-clipboard.txt")
            assert cleaned.returncode == 0, cleaned.stdout + cleaned.stderr


def test_cleanup_rejects_unsafe_paths_and_deletes_only_selected_child(tmp_path: Path) -> None:
    selected, _, _ = _prepare()
    survivor, _, _ = _prepare()
    nested = selected / "nested"
    nested.mkdir()
    (nested / "sentinel.txt").write_text("synthetic test data", encoding="utf-8")
    try:
        rejected = (
            str(FORENSIC_ROOT),
            "C:\\tmp",
            str(REPOSITORY),
            str(nested),
            str(FORENSIC_ROOT / "*"),
            str(selected / ".."),
            "relative-run",
        )
        for index, requested in enumerate(rejected):
            clipboard = tmp_path / f"rejected-{index}.txt"
            result = _cleanup(requested, clipboard)
            assert result.returncode != 0, requested
            assert "Validation: REJECTED" in result.stdout
            assert "Deleted: NO" in result.stdout
            assert "Errors (2>&1):" in result.stdout
            assert clipboard.read_text(encoding="utf-8").strip() == result.stdout.strip()
            assert selected.is_dir()
            assert survivor.is_dir()
            assert (nested / "sentinel.txt").is_file()

        clipboard = tmp_path / "approved.txt"
        result = _cleanup(str(selected), clipboard)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Validation: APPROVED" in result.stdout
        assert "Deleted: YES" in result.stdout
        assert f"Resolved run directory: {selected}" in result.stdout
        assert clipboard.read_text(encoding="utf-8").strip() == result.stdout.strip()
        assert not selected.exists()
        assert survivor.is_dir()
    finally:
        for run in (selected, survivor):
            if run.is_dir():
                result = _cleanup(str(run), tmp_path / f"{run.name}-final-clipboard.txt")
                assert result.returncode == 0, result.stdout + result.stderr


def test_cleanup_refuses_a_run_containing_a_directory_link(tmp_path: Path) -> None:
    run, _, _ = _prepare()
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "untouched.txt"
    marker.write_text("synthetic test data", encoding="utf-8")
    link = run / "redirected"
    try:
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (NotImplementedError, OSError):
            environment = os.environ.copy()
            environment.update({"SR_LINK": str(link), "SR_TARGET": str(outside)})
            junction = subprocess.run(
                [
                    _powershell(), "-NoProfile", "-Command",
                    "New-Item -ItemType Junction -Path $env:SR_LINK -Target $env:SR_TARGET "
                    "-ErrorAction Stop | Out-Null",
                ],
                cwd=REPOSITORY, env=environment, capture_output=True, text=True,
                encoding="utf-8", check=False,
            )
            if junction.returncode != 0:
                pytest.skip("Windows link and junction creation are unavailable")
        result = _cleanup(str(run), tmp_path / "link-refused-clipboard.txt")
        assert result.returncode != 0
        assert "Validation: REJECTED" in result.stdout
        assert "Deleted: NO" in result.stdout
        assert run.is_dir()
        assert marker.read_text(encoding="utf-8") == "synthetic test data"
    finally:
        if link.is_symlink():
            link.unlink()
        elif link.is_dir():
            link.rmdir()
        if run.is_dir():
            result = _cleanup(str(run), tmp_path / "link-final-clipboard.txt")
            assert result.returncode == 0, result.stdout + result.stderr
