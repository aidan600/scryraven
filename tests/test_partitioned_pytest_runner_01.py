from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "validation" / "run_partitioned_pytest.py"
SPEC = importlib.util.spec_from_file_location("partitioned_runner", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _tiny_repo(tmp_path: Path, baseline_tests: dict[str, str], candidate_tests: dict[str, str]) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "runner@example.invalid")
    _git(repo, "config", "user.name", "Runner Test")
    _git(repo, "remote", "add", "origin", "https://example.invalid/tiny.git")
    _write(repo / "proplex" / "__init__.py", "MARKER = 'baseline'\n")
    _write(repo / "core" / "__init__.py", "MARKER = 'baseline'\n")
    for name, body in baseline_tests.items():
        _write(repo / name, body)
    baseline = _commit(repo, "baseline")
    for path in (repo / "tests").glob("test*.py"):
        path.unlink()
    _write(repo / "proplex" / "__init__.py", "MARKER = 'candidate'\n")
    _write(repo / "core" / "__init__.py", "MARKER = 'candidate'\n")
    for name, body in candidate_tests.items():
        _write(repo / name, body)
    candidate = _commit(repo, "candidate")
    return repo, baseline, candidate


def _args(repo: Path, tmp_path: Path, baseline: str | None, candidate: str, **overrides: object) -> argparse.Namespace:
    values = {
        "repository": repo,
        "candidate": candidate,
        "baseline": baseline,
        "partitions": 2,
        "max_processes": 2,
        "process_timeout": 60.0,
        "packet_root": tmp_path / "packet",
        "work_root": tmp_path / "work",
        "allow_removed_test": [],
        "keep_worktrees": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_exact_ref_discovery_union_partition_and_filter(tmp_path: Path) -> None:
    repo, baseline, candidate = _tiny_repo(
        tmp_path,
        {"tests/test_a.py": "def test_a(): pass\n", "tests/test_b.py": "def test_b(): pass\n"},
        {"tests/test_b.py": "def test_b(): pass\n", "tests/test_c.py": "def test_c(): pass\n"},
    )
    baseline_set = runner.tracked_tests(repo, baseline)
    candidate_set = runner.tracked_tests(repo, candidate)
    assert baseline_set == ["tests/test_a.py", "tests/test_b.py"]
    assert candidate_set == ["tests/test_b.py", "tests/test_c.py"]
    partitions = runner.partition_union(set(baseline_set) | set(candidate_set), 2)
    assert partitions == [["tests/test_a.py", "tests/test_c.py"], ["tests/test_b.py"]]
    assert runner.filter_partitions(partitions, set(candidate_set)) == [["tests/test_c.py"], ["tests/test_b.py"]]


def test_removed_allowlist_is_exact_and_safe() -> None:
    assert runner.normalize_test_path(r"tests\test_exact.py") == "tests/test_exact.py"
    with pytest.raises(runner.UnsafeInvocation):
        runner.normalize_test_path("../tests/test_exact.py")
    with pytest.raises(runner.UnsafeInvocation):
        runner.normalize_test_path("tests")


def _result(side: str, nodes: list[str], classification: str = "valid-failures") -> object:
    return runner.ProcessResult(side, 1, 1 if nodes else 0, 0.1, classification, nodes, 1, len(nodes), 0, 0)


def test_aggregation_and_exit_contract() -> None:
    aggregate = runner.aggregate(
        [_result("baseline", ["shared", "fixed"]), _result("candidate", ["shared", "new"])],
        True,
        ["tests/test_added.py"],
        ["tests/test_removed.py"],
        ["tests/test_removed.py"],
    )
    assert aggregate["shared_failures_errors"] == ["shared"]
    assert aggregate["baseline_only_failures_errors"] == ["fixed"]
    assert aggregate["candidate_only_failures_errors"] == ["new"]
    assert aggregate["consequence"] == "regression"
    assert set(aggregate) == {
        "schema_version",
        "totals",
        "shared_failures_errors",
        "baseline_only_failures_errors",
        "candidate_only_failures_errors",
        "candidate_added_test_files",
        "candidate_removed_test_files",
        "authorized_removed_test_files",
        "unapproved_removed_test_files",
        "invalid_processes",
        "processes",
        "consequence",
    }
    assert runner.exit_for("passed") == 0
    assert runner.exit_for("regression") == 1
    assert runner.exit_for("infrastructure-invalid") == 2


def test_process_validity_and_malformed_junit(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    _write(junit, '<testsuite tests="1" failures="1" errors="0" skipped="0"><testcase classname="tests.test_x" name="test_bad"><failure/></testcase></testsuite>')
    valid = runner.classify_process(1, False, ["tests/test_x.py"], junit)
    assert valid.classification == "valid-failures"
    assert valid.failures_errors == ["tests/test_x.py::test_bad"]
    assert runner.classify_process(3, False, ["tests/test_x.py"], junit).classification == "infrastructure-invalid"
    junit.write_text("broken", encoding="utf-8")
    assert runner.classify_process(1, False, ["tests/test_x.py"], junit).classification == "infrastructure-invalid"


def test_environment_is_allowlisted_and_excludes_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_TOKEN", "do-not-record")
    assert runner.environment_fingerprint() == {
        "PYTHON_DOTENV_DISABLED": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }


def test_import_probe_rejects_wrong_commit_and_outside_path(tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    root.mkdir()
    good = {"observed_commit": "a" * 40, "modules": {"core": str(root / "core" / "__init__.py")}}
    runner.validate_import_probe(good, root, "a" * 40)
    with pytest.raises(runner.InfrastructureInvalid):
        runner.validate_import_probe({**good, "observed_commit": "b" * 40}, root, "a" * 40)
    with pytest.raises(runner.InfrastructureInvalid):
        runner.validate_import_probe({**good, "modules": {"core": str(tmp_path / "other.py")}}, root, "a" * 40)


def test_process_cap_is_enforced_without_sleep(tmp_path: Path) -> None:
    lock = threading.Lock()
    release = threading.Event()
    reached_cap = threading.Event()
    active = 0
    maximum = 0

    def fake(spec: object) -> object:
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
            if active == 2:
                reached_cap.set()
        assert release.wait(5)
        with lock:
            active -= 1
        return _result(spec.side, [])

    specs = [runner.ProcessSpec("candidate", i, tmp_path, ("tests/test_x.py",), tmp_path / f"{i}.log", tmp_path / f"{i}.xml", tmp_path / f"t{i}", 1) for i in range(4)]
    thread = threading.Thread(target=lambda: runner.run_bounded(specs, 2, fake))
    thread.start()
    assert reached_cap.wait(5)
    assert maximum == 2
    release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert maximum == 2


@pytest.mark.parametrize(
    ("baseline_body", "candidate_body", "expected", "shared", "baseline_only", "candidate_only"),
    [
        ("def test_value(): assert False\n", "def test_value(): assert False\n", 0, True, False, False),
        ("def test_value(): pass\n", "def test_value(): assert False\n", 1, False, False, True),
        ("def test_value(): assert False\n", "def test_value(): pass\n", 0, False, True, False),
    ],
)
def test_tiny_repo_parity_failure_attribution(
    tmp_path: Path, baseline_body: str, candidate_body: str, expected: int, shared: bool, baseline_only: bool, candidate_only: bool
) -> None:
    repo, baseline, candidate = _tiny_repo(tmp_path, {"tests/test_value.py": baseline_body}, {"tests/test_value.py": candidate_body})
    code, packet = runner.execute(_args(repo, tmp_path, baseline, candidate))
    aggregate = json.loads((packet / "aggregate.json").read_text(encoding="utf-8"))
    assert code == expected
    assert bool(aggregate["shared_failures_errors"]) is shared
    assert bool(aggregate["baseline_only_failures_errors"]) is baseline_only
    assert bool(aggregate["candidate_only_failures_errors"]) is candidate_only


def test_tiny_repo_added_failure_and_unapproved_removal(tmp_path: Path) -> None:
    added_root = tmp_path / "added"
    repo, baseline, candidate = _tiny_repo(
        added_root,
        {"tests/test_shared.py": "def test_shared(): pass\n"},
        {"tests/test_shared.py": "def test_shared(): pass\n", "tests/test_added.py": "def test_added(): assert False\n"},
    )
    code, packet = runner.execute(_args(repo, added_root, baseline, candidate))
    aggregate = json.loads((packet / "aggregate.json").read_text(encoding="utf-8"))
    assert code == 1
    assert aggregate["candidate_added_test_files"] == ["tests/test_added.py"]
    assert aggregate["candidate_only_failures_errors"]

    removed_root = tmp_path / "removed"
    repo, baseline, candidate = _tiny_repo(removed_root, {"tests/test_removed.py": "def test_removed(): pass\n"}, {})
    code, packet = runner.execute(_args(repo, removed_root, baseline, candidate))
    aggregate = json.loads((packet / "aggregate.json").read_text(encoding="utf-8"))
    assert code == 1
    assert aggregate["unapproved_removed_test_files"] == ["tests/test_removed.py"]


def test_tiny_repo_invalid_process_is_exit_two(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo, baseline, candidate = _tiny_repo(tmp_path, {"tests/test_x.py": "def test_x(): pass\n"}, {"tests/test_x.py": "def test_x(): pass\n"})
    monkeypatch.setattr(runner, "run_process", lambda spec: runner.ProcessResult(spec.side, spec.partition, 3, 0.1, "infrastructure-invalid", [], detail="pytest internal error"))
    monkeypatch.setattr(runner, "run_bounded", lambda specs, cap: [runner.run_process(spec) for spec in specs])
    code, packet = runner.execute(_args(repo, tmp_path, baseline, candidate))
    assert code == 2
    assert json.loads((packet / "aggregate.json").read_text(encoding="utf-8"))["consequence"] == "infrastructure-invalid"


def test_tiny_repo_imports_exact_worktrees_and_cleans_owned_paths(tmp_path: Path) -> None:
    repo, baseline, candidate = _tiny_repo(tmp_path, {"tests/test_x.py": "def test_x(): pass\n"}, {"tests/test_x.py": "def test_x(): pass\n"})
    code, packet = runner.execute(_args(repo, tmp_path, baseline, candidate))
    assert code == 0
    probes = json.loads((packet / "import-probes.json").read_text(encoding="utf-8"))
    assert {probe["observed_commit"] for probe in probes} == {baseline, candidate}
    for probe in probes:
        assert all(Path(path).is_relative_to(Path(probe["expected_root"])) for path in probe["modules"].values())
    cleanup = json.loads((packet / "cleanup.json").read_text(encoding="utf-8"))
    assert all(not Path(path).exists() for path in cleanup["owned_paths"])
    assert (packet / "aggregate.json").is_file()
    listing = _git(repo, "worktree", "list", "--porcelain")
    assert all(path not in listing for path in cleanup["owned_paths"])


def test_synthetic_candidate_only_cli(tmp_path: Path) -> None:
    repo, _, candidate = _tiny_repo(
        tmp_path,
        {"tests/test_x.py": "def test_x(): pass\n"},
        {"tests/test_x.py": "def test_x(): pass\n"},
    )
    packet = tmp_path / "cli-packet"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repository",
            str(repo),
            "--candidate",
            candidate,
            "--partitions",
            "2",
            "--max-processes",
            "1",
            "--packet-root",
            str(packet),
            "--work-root",
            str(tmp_path / "cli-work"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "consequence: passed" in completed.stdout
    assert json.loads((packet / "aggregate.json").read_text(encoding="utf-8"))["consequence"] == "passed"
