"""Run one human-approved local command without exposing an env file to the parent.

This operator-only credential-custody wrapper is not imported by ScryRaven.  It
does not sandbox a deliberately malicious target: redaction only replaces exact
secret values that appear unchanged in captured output.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

PRIVATE_ENV_FILE_PATH_ENV_VAR = "SCRYRAVEN_DOORMAN_ENV_FILE_PATH"
PRIVATE_NONCE_ENV_VAR = "SCRYRAVEN_DOORMAN_NONCE"
CONFIGURATION_EXIT_CODE = 2
TIMEOUT_EXIT_CODE = 124
MINIMUM_REDACTABLE_SECRET_LENGTH = 4
_MECHANICAL_ENVIRONMENT_NAMES = (
    "PATH",
    "Path",
    "SystemRoot",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "LOCALAPPDATA",
)
_SECRET_NAME_TERMS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "AUTH",
)


class BrokeredCommandError(ValueError):
    """Raised for a sanitized configuration failure."""


def main(argv: list[str] | None = None) -> int:
    supplied_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        option_argv, target_argv = _split_command(supplied_argv)
        if "--private-child" in option_argv:
            return _private_main(option_argv, target_argv)
        return _parent_main(option_argv, target_argv)
    except BrokeredCommandError as exc:
        print(f"brokered-command configuration failed: {exc}", file=sys.stderr)
        return CONFIGURATION_EXIT_CODE


def _parent_main(option_argv: Sequence[str], target_argv: list[str]) -> int:
    args = _parent_parser().parse_args(option_argv)
    repo_root = normalize_repository_root(args.repo_root)
    env_file_path = normalize_environment_file_path(args.env_file)
    stdout_path, stderr_path = validate_output_paths(
        repo_root=repo_root,
        stdout=args.stdout,
        stderr=args.stderr,
        replace_output=args.replace_output,
    )
    validate_target_argv(target_argv)
    if args.timeout_seconds <= 0:
        raise BrokeredCommandError("timeout_seconds_must_be_positive")

    nonce: str | None = secrets.token_urlsafe(32)
    child_env = private_child_environment(
        nonce=nonce,
        env_file_path=env_file_path,
        process_env=os.environ,
    )
    child_argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--private-child",
        "--repo-root",
        str(repo_root),
        "--stdout",
        str(stdout_path),
        "--stderr",
        str(stderr_path),
        "--timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.replace_output:
        child_argv.append("--replace-output")
    child_argv.extend(["--", *target_argv])
    try:
        completed = subprocess.run(
            child_argv,
            cwd=str(repo_root),
            env=child_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            shell=False,
        )
        return completed.returncode
    except OSError:
        return CONFIGURATION_EXIT_CODE
    finally:
        nonce = None
        child_env.clear()
        child_argv.clear()
        env_file_path = None


def _private_main(option_argv: Sequence[str], target_argv: list[str]) -> int:
    args = _private_parser().parse_args(option_argv)
    nonce = os.environ.get(PRIVATE_NONCE_ENV_VAR)
    env_file_path = os.environ.get(PRIVATE_ENV_FILE_PATH_ENV_VAR)
    if not nonce or not env_file_path:
        raise BrokeredCommandError("private_session_missing")
    repo_root = normalize_repository_root(args.repo_root)
    stdout_path, stderr_path = validate_output_paths(
        repo_root=repo_root,
        stdout=args.stdout,
        stderr=args.stderr,
        replace_output=args.replace_output,
    )
    validate_target_argv(target_argv)
    if args.timeout_seconds <= 0:
        raise BrokeredCommandError("timeout_seconds_must_be_positive")

    parsed_values = load_private_environment_file(Path(env_file_path))
    target_env = target_environment(parsed_values, os.environ)
    try:
        return _run_and_write_sanitized_output(
            target_argv=target_argv,
            repo_root=repo_root,
            target_env=target_env,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout_seconds=args.timeout_seconds,
            secret_values=secret_values_for_redaction(parsed_values),
        )
    finally:
        parsed_values.clear()
        target_env.clear()
        nonce = None
        env_file_path = None


def _run_and_write_sanitized_output(
    *,
    target_argv: Sequence[str],
    repo_root: Path,
    target_env: Mapping[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
    secret_values: Sequence[str],
) -> int:
    process = subprocess.Popen(
        list(target_argv),
        cwd=str(repo_root),
        env=dict(target_env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        **_target_process_group_options(),
    )
    timed_out = False
    raw_stdout: bytes | None = None
    raw_stderr: bytes | None = None
    try:
        raw_stdout, raw_stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_tree(process)
        raw_stdout, raw_stderr = process.communicate()
    finally:
        if process.poll() is None:
            _terminate_process_tree(process)
    try:
        stdout_path.write_text(
            redact_text(_normalize_captured_text(raw_stdout), secret_values),
            encoding="utf-8",
            newline="\n",
        )
        stderr_path.write_text(
            redact_text(_normalize_captured_text(raw_stderr), secret_values),
            encoding="utf-8",
            newline="\n",
        )
    finally:
        raw_stdout = None
        raw_stderr = None
    return TIMEOUT_EXIT_CODE if timed_out else process.returncode


def _normalize_captured_text(raw: bytes | None) -> str:
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")


def _parent_parser() -> argparse.ArgumentParser:
    parser = _common_parser()
    parser.add_argument("--env-file", required=True)
    return parser


def _private_parser() -> argparse.ArgumentParser:
    parser = _common_parser()
    parser.add_argument("--private-child", action="store_true", required=True)
    return parser


def _common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--timeout-seconds", type=float, required=True)
    parser.add_argument("--replace-output", action="store_true")
    return parser


def _split_command(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    try:
        boundary = list(argv).index("--")
    except ValueError as exc:
        raise BrokeredCommandError("target_argv_separator_required") from exc
    return list(argv[:boundary]), list(argv[boundary + 1 :])


def normalize_repository_root(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise BrokeredCommandError("repository_root_unavailable")
    return resolved


def normalize_environment_file_path(path: str | Path) -> Path:
    """Normalize and stat an env-file path without opening or parsing it."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise BrokeredCommandError("environment_file_unavailable")
    return resolved


def validate_output_paths(
    *,
    repo_root: Path,
    stdout: str | Path,
    stderr: str | Path,
    replace_output: bool,
) -> tuple[Path, Path]:
    stdout_path = _normalize_external_output_path(stdout, repo_root)
    stderr_path = _normalize_external_output_path(stderr, repo_root)
    if stdout_path == stderr_path:
        raise BrokeredCommandError("stdout_and_stderr_must_differ")
    for output_path in (stdout_path, stderr_path):
        if output_path.exists() and not replace_output:
            raise BrokeredCommandError("output_replacement_requires_authority")
    return stdout_path, stderr_path


def _normalize_external_output_path(path: str | Path, repo_root: Path) -> Path:
    supplied = Path(path).expanduser()
    if not supplied.is_absolute():
        raise BrokeredCommandError("output_path_must_be_absolute")
    resolved = supplied.resolve()
    if not resolved.parent.is_dir():
        raise BrokeredCommandError("output_parent_unavailable")
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return resolved
    raise BrokeredCommandError("output_path_must_be_outside_repository")


def validate_target_argv(target_argv: Sequence[str]) -> None:
    if not target_argv or not target_argv[0]:
        raise BrokeredCommandError("target_argv_required")


def _minimal_child_environment(process_env: Mapping[str, str]) -> dict[str, str]:
    env = {"PYTHONIOENCODING": "utf-8"}
    for name in _MECHANICAL_ENVIRONMENT_NAMES:
        value = process_env.get(name)
        if value:
            env[name] = value
    return env


def private_child_environment(
    *, nonce: str, env_file_path: Path, process_env: Mapping[str, str]
) -> dict[str, str]:
    if not nonce:
        raise BrokeredCommandError("private_session_missing")
    env = _minimal_child_environment(process_env)
    env[PRIVATE_NONCE_ENV_VAR] = nonce
    env[PRIVATE_ENV_FILE_PATH_ENV_VAR] = str(env_file_path)
    return env


def load_private_environment_file(path: Path) -> dict[str, str]:
    """Parse simple dotenv assignments inside the private child only."""

    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise BrokeredCommandError("environment_file_unavailable") from exc
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            raise BrokeredCommandError(f"invalid_environment_assignment_{line_number}")
        name, value = stripped.split("=", 1)
        name = name.strip()
        if not name.isidentifier():
            raise BrokeredCommandError(f"invalid_environment_name_{line_number}")
        value = _unquote_environment_value(value.strip(), line_number)
        values[name] = value
    return values


def _unquote_environment_value(value: str, line_number: int) -> str:
    if not value:
        return ""
    if value[0] in {"'", '"'}:
        if len(value) < 2 or value[-1] != value[0]:
            raise BrokeredCommandError(f"invalid_environment_value_{line_number}")
        return value[1:-1]
    return value


def target_environment(
    parsed_values: Mapping[str, str], process_env: Mapping[str, str]
) -> dict[str, str]:
    env = _minimal_child_environment(process_env)
    env.update(parsed_values)
    env.pop(PRIVATE_NONCE_ENV_VAR, None)
    env.pop(PRIVATE_ENV_FILE_PATH_ENV_VAR, None)
    return env


def secret_values_for_redaction(parsed_values: Mapping[str, str]) -> list[str]:
    return sorted(
        {
            value
            for name, value in parsed_values.items()
            if len(value) >= MINIMUM_REDACTABLE_SECRET_LENGTH
            and any(term in name.upper() for term in _SECRET_NAME_TERMS)
        },
        key=len,
        reverse=True,
    )


def redact_text(text: str, secret_values: Sequence[str]) -> str:
    redacted = text
    for value in secret_values:
        redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def _target_process_group_options() -> dict[str, int]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}  # type: ignore[dict-item]


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            shell=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
