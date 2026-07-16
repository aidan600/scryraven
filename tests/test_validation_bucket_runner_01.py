"""Focused contract tests for the validation bucket subprocess ordering.

Proof class: offline_tooling_contract.
Validation bucket: phase_focus.
Surface guarded: scripts/validation/run_bucket.py command sequencing.
Expected cost: no pytest subprocesses; subprocess.call is replaced by a fake.
Promotion posture: remain phase_focus because fast_pr exercises the guard directly.
Why not fast_pr: adding the runner's own unit test would duplicate every fast_pr run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import scripts.validation.run_bucket as runner


def _configure_runner(
    monkeypatch: Any,
    tmp_path: Path,
    *,
    return_codes: list[int],
) -> list[dict[str, Any]]:
    bucket_dir = tmp_path / "buckets"
    bucket_dir.mkdir()
    (bucket_dir / "fast_pr.txt").write_text(
        "tests/test_sentinel.py::test_small\n",
        encoding="utf-8",
    )
    calls: list[dict[str, Any]] = []

    def fake_call(command: list[str], *, cwd: Path, env: dict[str, str]) -> int:
        calls.append({"command": list(command), "cwd": cwd, "env": dict(env)})
        return return_codes[len(calls) - 1]

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BUCKET_DIR", bucket_dir)
    monkeypatch.setattr(runner.subprocess, "call", fake_call)
    monkeypatch.setattr(runner.sys, "executable", "python-for-test")
    monkeypatch.delenv("SCRYRAVEN_PYTEST_BASETEMP", raising=False)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    return calls


def test_fast_pr_runs_full_collection_guard_before_selected_tests(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    calls = _configure_runner(monkeypatch, tmp_path, return_codes=[0, 0])

    assert runner.main(["fast_pr"]) == 0

    assert len(calls) == 2
    guard, selected = calls
    assert guard["command"][:5] == [
        "python-for-test",
        "-m",
        "pytest",
        "-q",
        "--collect-only",
    ]
    assert "tests/test_sentinel.py::test_small" not in guard["command"]
    assert selected["command"][-1] == "tests/test_sentinel.py::test_small"
    assert "--collect-only" not in selected["command"]
    assert guard["env"]["PYTHON_DOTENV_DISABLED"] == "1"
    assert selected["env"]["PYTHON_DOTENV_DISABLED"] == "1"


def test_fast_pr_returns_collection_failure_without_running_selected_tests(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    calls = _configure_runner(monkeypatch, tmp_path, return_codes=[17])

    assert runner.main(["fast_pr"]) == 17
    assert len(calls) == 1
    assert "--collect-only" in calls[0]["command"]


def test_fast_pr_collect_only_keeps_guard_and_selected_collection_coherent(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    calls = _configure_runner(monkeypatch, tmp_path, return_codes=[0, 0])

    assert runner.main(["fast_pr", "--collect-only"]) == 0
    assert len(calls) == 2
    assert "--collect-only" in calls[0]["command"]
    assert "--collect-only" in calls[1]["command"]
    assert calls[1]["command"][-1] == "tests/test_sentinel.py::test_small"
