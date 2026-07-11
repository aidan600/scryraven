"""Deterministic offline pytest partitions with optional baseline parity.

This is developer-validation orchestration, not product runtime scheduling.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Sequence

SCHEMA_VERSION = "scryraven.partitioned-pytest/v1"
EXIT_PASS = 0
EXIT_REGRESSION = 1
EXIT_INVALID = 2
EXIT_UNSAFE = 3
MAX_PARTITIONS = 128
MAX_PROCESSES = 16
DEFAULT_TIMEOUT = 1800.0
TEST_RE = re.compile(r"^tests/(?:.*/)?test[^/]*\.py$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
ALLOWED_ENV = ("PYTHON_DOTENV_DISABLED", "PYTEST_DISABLE_PLUGIN_AUTOLOAD")


class UnsafeInvocation(RuntimeError):
    """Preflight refusal before runner-owned mutation."""


class InfrastructureInvalid(RuntimeError):
    """Execution cannot support a semantic validation verdict."""


@dataclasses.dataclass(frozen=True)
class ProcessSpec:
    side: str
    partition: int
    cwd: Path
    manifest: tuple[str, ...]
    log_path: Path
    junit_path: Path
    basetemp: Path
    timeout: float


@dataclasses.dataclass
class ProcessResult:
    side: str
    partition: int
    exit_code: int | None
    duration_seconds: float
    classification: str
    failures_errors: list[str]
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    timed_out: bool = False
    detail: str = ""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def git(repo: Path, *args: str, timeout: float = 30.0) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise UnsafeInvocation(f"git {' '.join(args)} failed: {message}")
    return completed.stdout.strip()


def resolve_commit(repo: Path, ref: str) -> str:
    sha = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if not SHA_RE.fullmatch(sha):
        raise UnsafeInvocation(f"ref did not resolve to an immutable commit: {ref}")
    return sha.lower()


def is_clean(repo: Path) -> bool:
    return not git(repo, "status", "--porcelain", "--untracked-files=all")


def normalize_test_path(raw: str) -> str:
    value = raw.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not TEST_RE.fullmatch(value):
        raise UnsafeInvocation(f"unsafe removed-test allowlist path: {raw}")
    return value


def tracked_tests(repo: Path, sha: str) -> list[str]:
    output = git(repo, "ls-tree", "-r", "--name-only", sha, "--", "tests")
    return sorted(line for line in output.splitlines() if TEST_RE.fullmatch(line))


def partition_union(paths: Iterable[str], count: int) -> list[list[str]]:
    if not 1 <= count <= MAX_PARTITIONS:
        raise UnsafeInvocation(f"partitions must be between 1 and {MAX_PARTITIONS}")
    partitions = [[] for _ in range(count)]
    for index, path in enumerate(sorted(set(paths))):
        partitions[index % count].append(path)
    return partitions


def filter_partitions(partitions: Sequence[Sequence[str]], present: set[str]) -> list[list[str]]:
    return [[path for path in partition if path in present] for partition in partitions]


def environment_fingerprint() -> dict[str, str]:
    return {name: "1" for name in ALLOWED_ENV}


def parse_junit(path: Path) -> dict[str, object]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise InfrastructureInvalid(f"missing or malformed JUnit: {path}: {exc}") from exc
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise InfrastructureInvalid(f"JUnit contains no test suite: {path}")
    totals = {key: sum(int(s.get(key, "0")) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    nodes: set[str] = set()
    unstable_error = False
    for case in root.iter("testcase"):
        bad = case.find("failure") is not None or case.find("error") is not None
        if not bad:
            continue
        classname = case.get("classname", "").replace(".", "/")
        name = case.get("name", "")
        if not name:
            unstable_error = True
            continue
        node = f"{classname}.py::{name}" if classname else name
        nodes.add(node)
    if unstable_error or len(nodes) < totals["failures"] + totals["errors"]:
        raise InfrastructureInvalid("JUnit cannot provide stable failure/error attribution")
    return {**totals, "failures_errors": sorted(nodes)}


def classify_process(exit_code: int | None, timed_out: bool, manifest: Sequence[str], junit: Path) -> ProcessResult:
    if timed_out:
        return ProcessResult("", 0, exit_code, 0.0, "infrastructure-invalid", [], timed_out=True, detail="timeout")
    if exit_code not in (0, 1):
        return ProcessResult("", 0, exit_code, 0.0, "infrastructure-invalid", [], detail=f"pytest exit {exit_code}")
    try:
        parsed = parse_junit(junit)
    except InfrastructureInvalid as exc:
        return ProcessResult("", 0, exit_code, 0.0, "infrastructure-invalid", [], detail=str(exc))
    tests = int(parsed["tests"])
    if manifest and tests == 0:
        return ProcessResult("", 0, exit_code, 0.0, "infrastructure-invalid", [], detail="no tests collected")
    failures = int(parsed["failures"])
    errors = int(parsed["errors"])
    if exit_code == 0 and (failures or errors):
        return ProcessResult("", 0, exit_code, 0.0, "infrastructure-invalid", [], detail="exit/JUnit mismatch")
    if exit_code == 1 and not (failures or errors):
        return ProcessResult("", 0, exit_code, 0.0, "infrastructure-invalid", [], detail="exit/JUnit mismatch")
    return ProcessResult(
        "", 0, exit_code, 0.0, "valid-failures" if exit_code == 1 else "valid-pass",
        list(parsed["failures_errors"]), tests, failures, errors, int(parsed["skipped"]),
    )


def run_process(spec: ProcessSpec, python: str = sys.executable) -> ProcessResult:
    spec.log_path.parent.mkdir(parents=True, exist_ok=True)
    spec.junit_path.parent.mkdir(parents=True, exist_ok=True)
    spec.basetemp.parent.mkdir(parents=True, exist_ok=True)
    args = [python, "-m", "pytest", "-q", f"--basetemp={spec.basetemp}", f"--junitxml={spec.junit_path}", *spec.manifest]
    env = os.environ.copy()
    env.update(environment_fingerprint())
    started = time.monotonic()
    timed_out = False
    exit_code: int | None = None
    with spec.log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("command: " + json.dumps(args) + "\n")
        try:
            completed = subprocess.run(args, cwd=spec.cwd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=spec.timeout, check=False)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            log.write(f"\nTIMEOUT after {spec.timeout} seconds\n")
    result = classify_process(exit_code, timed_out, spec.manifest, spec.junit_path)
    result.side = spec.side
    result.partition = spec.partition
    result.duration_seconds = round(time.monotonic() - started, 3)
    return result


def run_bounded(specs: Sequence[ProcessSpec], cap: int, executor: Callable[[ProcessSpec], ProcessResult] = run_process) -> list[ProcessResult]:
    if not 1 <= cap <= MAX_PROCESSES:
        raise UnsafeInvocation(f"max-processes must be between 1 and {MAX_PROCESSES}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=cap) as pool:
        futures = [pool.submit(executor, spec) for spec in specs]
        return [future.result() for future in futures]


def validate_import_probe(probe: dict[str, object], expected_root: Path, expected_sha: str) -> None:
    if probe.get("observed_commit") != expected_sha:
        raise InfrastructureInvalid("import probe observed the wrong commit")
    root = expected_root.resolve()
    for name, raw in dict(probe.get("modules", {})).items():
        try:
            Path(str(raw)).resolve().relative_to(root)
        except ValueError as exc:
            raise InfrastructureInvalid(f"{name} resolved outside detached worktree: {raw}") from exc


def import_probe(worktree: Path, expected_sha: str, python: str = sys.executable) -> dict[str, object]:
    code = (
        "import json,pathlib,subprocess,sys; sys.path.insert(0,str(pathlib.Path.cwd())); import proplex,core; "
        "print(json.dumps({'python_executable':sys.executable,'observed_commit':"
        "subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),"
        "'modules':{'proplex':str(pathlib.Path(proplex.__file__).resolve()),"
        "'core':str(pathlib.Path(core.__file__).resolve())}}))"
    )
    env = os.environ.copy()
    env.update(environment_fingerprint())
    completed = subprocess.run([python, "-I", "-c", code], cwd=worktree, env=env, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode:
        raise InfrastructureInvalid(f"import probe failed for {worktree}: {completed.stderr.strip()}")
    try:
        probe = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise InfrastructureInvalid("import probe returned malformed JSON") from exc
    probe["expected_root"] = str(worktree.resolve())
    probe["expected_commit"] = expected_sha
    validate_import_probe(probe, worktree, expected_sha)
    return probe


def aggregate(results: Sequence[ProcessResult], baseline: bool, added: Sequence[str], removed: Sequence[str], allowed_removed: Sequence[str]) -> dict[str, object]:
    invalid = [dataclasses.asdict(r) for r in results if r.classification == "infrastructure-invalid"]
    by_side = {side: sorted({node for r in results if r.side == side for node in r.failures_errors}) for side in ("baseline", "candidate")}
    candidate = set(by_side["candidate"])
    base = set(by_side["baseline"])
    unapproved = sorted(set(removed) - set(allowed_removed))
    shared = sorted(base & candidate)
    baseline_only = sorted(base - candidate)
    candidate_only = sorted(candidate - base) if baseline else sorted(candidate)
    consequence = "infrastructure-invalid" if invalid else "regression" if candidate_only or unapproved else "passed"
    return {
        "schema_version": SCHEMA_VERSION,
        "totals": {
            side: {key: sum(getattr(r, key) for r in results if r.side == side) for key in ("tests", "failures", "errors", "skipped")}
            for side in ("baseline", "candidate") if baseline or side == "candidate"
        },
        "shared_failures_errors": shared,
        "baseline_only_failures_errors": baseline_only,
        "candidate_only_failures_errors": candidate_only,
        "candidate_added_test_files": sorted(added),
        "candidate_removed_test_files": sorted(removed),
        "authorized_removed_test_files": sorted(set(removed) & set(allowed_removed)),
        "unapproved_removed_test_files": unapproved,
        "invalid_processes": invalid,
        "processes": [dataclasses.asdict(r) for r in sorted(results, key=lambda item: (item.partition, item.side))],
        "consequence": consequence,
    }


def exit_for(consequence: str) -> int:
    return {"passed": EXIT_PASS, "regression": EXIT_REGRESSION, "infrastructure-invalid": EXIT_INVALID}[consequence]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summary_lines(semantic: dict[str, object], configuration: dict[str, object], packet: Path) -> list[str]:
    lines = [
        f"consequence: {semantic.get('consequence')}",
        f"packet: {packet}",
        f"repository: {configuration['repository']['root']}",
        f"candidate: {configuration['candidate_sha']}",
        f"baseline: {configuration['baseline_sha'] or 'not-requested'}",
    ]
    for side, totals in dict(semantic.get("totals", {})).items():
        lines.append(f"{side} totals: " + ", ".join(f"{key}={value}" for key, value in dict(totals).items()))
    for key in (
        "shared_failures_errors",
        "baseline_only_failures_errors",
        "candidate_only_failures_errors",
        "candidate_added_test_files",
        "candidate_removed_test_files",
        "authorized_removed_test_files",
        "unapproved_removed_test_files",
    ):
        lines.append(f"{key}: {json.dumps(semantic.get(key, []))}")
    for process in semantic.get("processes", []):
        lines.append(
            "process: "
            f"{process['side']}-p{process['partition']} "
            f"classification={process['classification']} exit={process['exit_code']} "
            f"duration_seconds={process['duration_seconds']}"
        )
    for invalid in semantic.get("invalid_processes", []):
        lines.append(f"invalid process: {invalid['side']}-p{invalid['partition']} {invalid['detail']}")
    if semantic.get("runner_error"):
        lines.append(f"runner error: {semantic['runner_error']}")
    return lines


def ensure_outside(path: Path, repo: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(repo.resolve())
    except ValueError:
        return resolved
    raise UnsafeInvocation(f"{label} must be outside the tracked repository: {resolved}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--candidate", default="HEAD")
    parser.add_argument("--baseline")
    parser.add_argument("--partitions", type=int, default=4)
    parser.add_argument("--max-processes", type=int, default=2)
    parser.add_argument("--process-timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--packet-root", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--allow-removed-test", action="append", default=[])
    parser.add_argument("--keep-worktrees", action="store_true")
    return parser


def execute(args: argparse.Namespace) -> tuple[int, Path]:
    repo = Path(git(args.repository, "rev-parse", "--show-toplevel")).resolve()
    if args.candidate == "HEAD" and not is_clean(repo):
        raise UnsafeInvocation("--candidate HEAD requires a clean primary worktree")
    if args.candidate != "HEAD" and not is_clean(repo) and not SHA_RE.fullmatch(args.candidate):
        raise UnsafeInvocation("a dirty primary worktree requires an explicit 40-character candidate SHA")
    if not 1 <= args.partitions <= MAX_PARTITIONS:
        raise UnsafeInvocation(f"partitions must be between 1 and {MAX_PARTITIONS}")
    if not 1 <= args.max_processes <= MAX_PROCESSES:
        raise UnsafeInvocation(f"max-processes must be between 1 and {MAX_PROCESSES}")
    if args.process_timeout <= 0:
        raise UnsafeInvocation("process-timeout must be positive")
    candidate_sha = resolve_commit(repo, args.candidate)
    baseline_sha = resolve_commit(repo, args.baseline) if args.baseline else None
    allowed_removed = sorted({normalize_test_path(path) for path in args.allow_removed_test})
    run_id = uuid.uuid4().hex[:10]
    temp_root = Path("C:/tmp") if os.name == "nt" else Path(tempfile.gettempdir())
    packet = ensure_outside(args.packet_root or temp_root / "srval-packets" / run_id, repo, "packet-root")
    work_root = ensure_outside(args.work_root or temp_root / f"srval-{run_id}", repo, "work-root")
    if packet.exists() or work_root.exists():
        raise UnsafeInvocation("packet-root and work-root must not already exist")
    candidate_tests = tracked_tests(repo, candidate_sha)
    baseline_tests = tracked_tests(repo, baseline_sha) if baseline_sha else []
    union = sorted(set(candidate_tests) | set(baseline_tests))
    added = sorted(set(candidate_tests) - set(baseline_tests)) if baseline_sha else []
    removed = sorted(set(baseline_tests) - set(candidate_tests))
    unknown_allowed = sorted(set(allowed_removed) - set(removed))
    if unknown_allowed:
        raise UnsafeInvocation(f"removed-test allowlist paths are not candidate removals: {unknown_allowed}")
    partitions = partition_union(union, args.partitions)
    side_partitions = {"candidate": filter_partitions(partitions, set(candidate_tests))}
    if baseline_sha:
        side_partitions["baseline"] = filter_partitions(partitions, set(baseline_tests))

    started = utc_now()
    configuration = {
        "schema_version": SCHEMA_VERSION,
        "repository": {"root": str(repo), "origin": git(repo, "remote", "get-url", "origin")},
        "candidate_sha": candidate_sha, "baseline_sha": baseline_sha,
        "partitions": args.partitions, "algorithm": "sorted-union-stable-round-robin-v1",
        "max_processes": args.max_processes, "process_timeout_seconds": args.process_timeout,
        "python_executable": sys.executable, "pytest_flags": ["-q", "--basetemp=<unique>", "--junitxml=<unique>", "<explicit-manifest>"],
        "environment": environment_fingerprint(), "removed_test_allowlist": allowed_removed,
        "packet_root": str(packet), "work_root": str(work_root), "started_at": started,
    }
    packet.mkdir(parents=True)
    work_root.mkdir(parents=True)
    write_json(packet / "configuration.json", configuration)
    created: list[Path] = []
    cleanup: list[dict[str, object]] = []
    semantic: dict[str, object] | None = None
    try:
        for index, manifest in enumerate(partitions, 1):
            (packet / "manifests").mkdir(exist_ok=True)
            (packet / "manifests" / f"partition-{index}-union.txt").write_text("\n".join(manifest) + ("\n" if manifest else ""), encoding="utf-8")
            for side, per_side in side_partitions.items():
                values = per_side[index - 1]
                (packet / "manifests" / f"partition-{index}-{side}.txt").write_text("\n".join(values) + ("\n" if values else ""), encoding="utf-8")
        shas = {"candidate": candidate_sha, **({"baseline": baseline_sha} if baseline_sha else {})}
        probes: list[dict[str, object]] = []
        worktrees: dict[str, Path] = {}
        for side, sha in shas.items():
            path = work_root / ("c" if side == "candidate" else "b")
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(path), str(sha)], capture_output=True, text=True, timeout=60, check=True)
            created.append(path.resolve())
            worktrees[side] = path
            probe = import_probe(path, str(sha))
            probe["side"] = side
            probes.append(probe)
        write_json(packet / "import-probes.json", probes)
        specs: list[ProcessSpec] = []
        for side, per_side in side_partitions.items():
            for index, manifest in enumerate(per_side, 1):
                if not manifest:
                    continue
                specs.append(ProcessSpec(side, index, worktrees[side], tuple(manifest), packet / "logs" / f"{side}-p{index}.log", packet / "junit" / f"{side}-p{index}.xml", work_root / "tmp" / f"{side[0]}{index}", args.process_timeout))
        results = run_bounded(specs, args.max_processes)
        semantic = aggregate(results, bool(baseline_sha), added, removed, allowed_removed)
        write_json(packet / "process-summary.json", [dataclasses.asdict(r) for r in results])
        write_json(packet / "aggregate.json", semantic)
    except UnsafeInvocation:
        raise
    except (KeyboardInterrupt, Exception) as exc:
        semantic = semantic or {"schema_version": SCHEMA_VERSION, "consequence": "infrastructure-invalid", "runner_error": f"{type(exc).__name__}: {exc}"}
        write_json(packet / "aggregate.json", semantic)
    finally:
        if not args.keep_worktrees:
            for path in reversed(created):
                command = ["git", "-C", str(repo), "worktree", "remove", "--force", str(path)]
                completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
                item = {"path": str(path), "command": command, "exit_code": completed.returncode, "detail": completed.stderr.strip()}
                cleanup.append(item)
                if completed.returncode and semantic is not None:
                    semantic["semantic_consequence_before_cleanup"] = semantic.get("consequence")
                    semantic["consequence"] = "infrastructure-invalid"
                    semantic.setdefault("cleanup_failures", []).append(item)
            if all(item["exit_code"] == 0 for item in cleanup):
                try:
                    shutil.rmtree(work_root)
                except OSError as exc:
                    if semantic is not None:
                        semantic["semantic_consequence_before_cleanup"] = semantic.get("consequence")
                        semantic["consequence"] = "infrastructure-invalid"
                        instruction = (
                            f"Remove-Item -LiteralPath '{str(work_root).replace(chr(39), chr(39) * 2)}' -Recurse -Force"
                            if os.name == "nt"
                            else f"rm -rf -- {shlex.quote(str(work_root))}"
                        )
                        semantic.setdefault("cleanup_failures", []).append(
                            {"path": str(work_root), "detail": str(exc), "operator_instruction": instruction}
                        )
        cleanup_posture = {"keep_worktrees": args.keep_worktrees, "owned_paths": [str(p) for p in created], "attempts": cleanup}
        write_json(packet / "cleanup.json", cleanup_posture)
        if semantic is not None:
            semantic["cleanup_posture"] = cleanup_posture
            semantic["ended_at"] = utc_now()
            write_json(packet / "aggregate.json", semantic)
            lines = summary_lines(semantic, configuration, packet)
            for failure in semantic.get("cleanup_failures", []):
                lines.append(f"cleanup failed: {failure.get('path')}")
                if failure.get("command"):
                    lines.append("operator instruction: " + subprocess.list2cmdline(failure["command"]))
                elif failure.get("operator_instruction"):
                    lines.append("operator instruction: " + failure["operator_instruction"])
            (packet / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return exit_for(str(semantic["consequence"])), packet


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        code, packet = execute(args)
    except UnsafeInvocation as exc:
        print(f"unsafe invocation: {exc}", file=sys.stderr)
        return EXIT_UNSAFE
    print(f"artifact packet: {packet}")
    print((packet / "summary.txt").read_text(encoding="utf-8"), end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
