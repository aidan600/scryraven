"""Offline coverage for the operator-only brokered command doorman."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_brokered_command_once as doorman


def _write_env(path: Path, text: str = "NORMAL=value\nAPI_KEY=fake-secret-value\n") -> Path:  # pragma: allowlist secret
    path.write_text(text, encoding="utf-8")
    return path


def _arguments(
    *,
    repo_root: Path,
    env_file: Path,
    stdout: Path,
    stderr: Path,
    timeout: float = 10,
    replace_output: bool = False,
) -> list[str]:
    args = [
        "--repo-root",
        str(repo_root),
        "--env-file",
        str(env_file),
        "--stdout",
        str(stdout),
        "--stderr",
        str(stderr),
        "--timeout-seconds",
        str(timeout),
    ]
    if replace_output:
        args.append("--replace-output")
    return args


def _run(
    *,
    repo_root: Path,
    env_file: Path,
    stdout: Path,
    stderr: Path,
    command: list[str],
    timeout: float = 10,
    replace_output: bool = False,
) -> int:
    return doorman.main(
        [
            *_arguments(
                repo_root=repo_root,
                env_file=env_file,
                stdout=stdout,
                stderr=stderr,
                timeout=timeout,
                replace_output=replace_output,
            ),
            "--",
            *command,
        ]
    )


def test_parent_stats_but_does_not_open_or_parse_environment_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    env_file = _write_env(tmp_path / "private.env", "not dotenv syntax\n")
    observed: dict[str, object] = {}

    def forbidden_read(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("public parent must not read the env file")

    def fake_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        env = kwargs.get("env")
        observed["argv"] = list(argv)
        observed["kwargs"] = {
            **kwargs,
            "env": dict(env) if isinstance(env, dict) else env,
        }
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(Path, "read_text", forbidden_read)
    monkeypatch.setattr(doorman.subprocess, "run", fake_run)
    assert (
        _run(
            repo_root=repo_root,
            env_file=env_file,
            stdout=output_root / "stdout.txt",
            stderr=output_root / "stderr.txt",
            command=[sys.executable, "-c", "raise SystemExit(0)"],
        )
        == 0
    )
    child_argv = observed["argv"]
    assert isinstance(child_argv, list)
    assert str(env_file) not in child_argv
    assert "--env-file" not in child_argv
    assert observed["kwargs"]["shell"] is False  # type: ignore[index]
    child_env = observed["kwargs"]["env"]  # type: ignore[index]
    assert isinstance(child_env, dict)
    assert child_env[doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR] == str(env_file.resolve())
    assert doorman.PRIVATE_NONCE_ENV_VAR in child_env
    assert observed["kwargs"]["stdout"] is subprocess.DEVNULL  # type: ignore[index]
    assert observed["kwargs"]["stderr"] is subprocess.DEVNULL  # type: ignore[index]


def test_private_mode_requires_nonce(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    monkeypatch.delenv(doorman.PRIVATE_NONCE_ENV_VAR, raising=False)
    monkeypatch.delenv(doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR, raising=False)
    assert doorman.main([
        "--private-child",
        "--repo-root", str(repo_root),
        "--stdout", str(output_root / "out.txt"),
        "--stderr", str(output_root / "err.txt"),
        "--timeout-seconds", "1", "--", sys.executable, "-c", "pass",
    ]) == doorman.CONFIGURATION_EXIT_CODE


def test_target_receives_env_literal_argv_cwd_and_redacted_output(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    env_file = _write_env(tmp_path / "private.env")
    stdout = output_root / "stdout.txt"
    stderr = output_root / "stderr.txt"
    literal_argv = ["space value", "&|<>^%", "punctuation;()[]{}"]
    command = [
        sys.executable,
        "-c",
        (
            "import json, os, sys; "
            "print(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd(), "
            "'normal': os.environ['NORMAL'], 'secret': os.environ['API_KEY']})); "
            "print(os.environ['API_KEY'], file=sys.stderr)"
        ),
        *literal_argv,
    ]
    assert _run(
        repo_root=repo_root,
        env_file=env_file,
        stdout=stdout,
        stderr=stderr,
        command=command,
    ) == 0
    rendered = stdout.read_text(encoding="utf-8")
    payload = json.loads(rendered)
    assert payload["argv"] == literal_argv
    assert payload["cwd"] == str(repo_root)
    assert payload["normal"] == "value"
    assert payload["secret"] == "[REDACTED]"
    assert stderr.read_text(encoding="utf-8") == "[REDACTED]\n"
    assert str(env_file) not in rendered


def test_multiple_secret_values_redact_longest_first_and_preserve_nonsecret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    secret = "shared-secret-value"  # pragma: allowlist secret
    env_file = _write_env(
        tmp_path / "private.env",
        f"AUTH_TOKEN={secret}\nPASSWORD={secret}-long\nNORMAL=retained\n",
    )
    stdout = output_root / "stdout.txt"
    stderr = output_root / "stderr.txt"
    command = [
        sys.executable,
        "-c",
        "import os, sys; print(os.environ['AUTH_TOKEN'], os.environ['PASSWORD'], os.environ['NORMAL']); print(os.environ['PASSWORD'], file=sys.stderr)",
    ]
    assert _run(
        repo_root=repo_root, env_file=env_file, stdout=stdout, stderr=stderr, command=command
    ) == 0
    captured = capsys.readouterr()
    for rendered in (stdout.read_text(), stderr.read_text(), captured.out, captured.err):
        assert secret not in rendered
    assert stdout.read_text() == "[REDACTED] [REDACTED] retained\n"
    assert stderr.read_text() == "[REDACTED]\n"


@pytest.mark.parametrize("exit_code", [0, 17])
def test_target_exit_codes_are_preserved(tmp_path: Path, exit_code: int) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    assert _run(
        repo_root=repo_root,
        env_file=_write_env(tmp_path / "private.env"),
        stdout=output_root / "stdout.txt",
        stderr=output_root / "stderr.txt",
        command=[sys.executable, "-c", f"raise SystemExit({exit_code})"],
    ) == exit_code


def test_private_child_uses_one_shell_free_target_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    env_file = _write_env(tmp_path / "private.env")
    observed_argv: list[list[str]] = []
    observed_kwargs: list[dict[str, object]] = []

    class FakeProcess:
        returncode = 0
        pid = 1

        def __init__(self, argv: list[str], **kwargs: object) -> None:
            observed_argv.append(list(argv))
            observed_kwargs.append(kwargs)

        def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
            return b"ok", b""

        def poll(self) -> int:
            return 0

    monkeypatch.setattr(doorman.subprocess, "Popen", FakeProcess)
    env = {
        doorman.PRIVATE_NONCE_ENV_VAR: "nonce",
        doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR: str(env_file),
        "PATH": os.environ["PATH"],
    }
    monkeypatch.setattr(doorman.os, "environ", env)
    assert doorman.main([
        "--private-child", "--repo-root", str(repo_root), "--stdout", str(output_root / "out.txt"),
        "--stderr", str(output_root / "err.txt"), "--timeout-seconds", "1", "--",
        "literal-command", "argument with spaces",
    ]) == 0
    assert observed_argv == [["literal-command", "argument with spaces"]]
    assert len(observed_kwargs) == 1
    assert observed_kwargs[0]["shell"] is False
    assert observed_kwargs[0]["cwd"] == str(repo_root.resolve())
    target_env = observed_kwargs[0]["env"]
    assert isinstance(target_env, dict)
    assert target_env["API_KEY"] == "fake-secret-value"  # pragma: allowlist secret
    assert doorman.PRIVATE_NONCE_ENV_VAR not in target_env
    assert doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR not in target_env
    assert (output_root / "out.txt").read_text() == "ok"


def test_timeout_terminates_target_tree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    descendant_marker = output_root / "descendant-survived.txt"
    descendant_code = (
        "import pathlib, sys, time; time.sleep(1.5); "
        "pathlib.Path(sys.argv[1]).write_text('unexpected')"
    )
    target_code = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]]); "
        "time.sleep(30)"
    )
    assert _run(
        repo_root=repo_root,
        env_file=_write_env(tmp_path / "private.env"),
        stdout=output_root / "stdout.txt",
        stderr=output_root / "stderr.txt",
        timeout=0.2,
        command=[sys.executable, "-c", target_code, descendant_code, str(descendant_marker)],
    ) == doorman.TIMEOUT_EXIT_CODE
    time.sleep(2)
    assert not descendant_marker.exists()


def test_output_path_guards_and_explicit_replacement(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    env_file = _write_env(tmp_path / "private.env")
    command = [sys.executable, "-c", "print('safe')"]
    inside = repo_root / "inside.txt"
    assert _run(
        repo_root=repo_root, env_file=env_file, stdout=inside, stderr=output_root / "err.txt", command=command
    ) == doorman.CONFIGURATION_EXIT_CODE
    same = output_root / "same.txt"
    assert _run(
        repo_root=repo_root, env_file=env_file, stdout=same, stderr=same, command=command
    ) == doorman.CONFIGURATION_EXIT_CODE
    stdout = output_root / "stdout.txt"
    stderr = output_root / "stderr.txt"
    stdout.write_text("existing")
    assert _run(
        repo_root=repo_root, env_file=env_file, stdout=stdout, stderr=stderr, command=command
    ) == doorman.CONFIGURATION_EXIT_CODE
    assert _run(
        repo_root=repo_root, env_file=env_file, stdout=stdout, stderr=stderr, command=command, replace_output=True
    ) == 0
    assert stdout.read_text() == "safe\n"


def test_product_packages_do_not_import_operator_launcher() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for package_name in ("scryraven", "proplex", "core"):
        package = root / package_name
        if not package.exists():
            continue
        for path in package.rglob("*.py"):
            if "run_brokered_command_once" in path.read_text(encoding="utf-8"):
                offenders.append(path.relative_to(root))
    assert offenders == []


def test_no_private_launcher_value_enters_target_environment() -> None:
    parsed = {"API_KEY": "fake-secret-value", "NORMAL": "safe"}  # pragma: allowlist secret
    child_env = doorman.private_child_environment(
        nonce="nonce", env_file_path=Path("C:/private.env"), process_env={}
    )
    target_env = doorman.target_environment(parsed, child_env)
    assert target_env["API_KEY"] == "fake-secret-value"  # pragma: allowlist secret
    assert doorman.PRIVATE_NONCE_ENV_VAR not in target_env
    assert doorman.PRIVATE_ENV_FILE_PATH_ENV_VAR not in target_env


def test_utf8_bom_prefixed_secret_loads_and_redacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_root = tmp_path / "external"
    output_root.mkdir()
    secret = "bom-fake-secret-value"  # pragma: allowlist secret
    env_file = tmp_path / "private.env"
    env_file.write_bytes(b"\xef\xbb\xbfAPI_KEY=" + secret.encode("utf-8") + b"\nNORMAL=ok\n")
    stdout = output_root / "stdout.txt"
    stderr = output_root / "stderr.txt"
    command = [
        sys.executable,
        "-c",
        (
            "import json, os, sys; "
            "print(json.dumps({"
            "'keys': sorted(k for k in os.environ if k.startswith('API') or k == 'NORMAL'), "
            "'api_key': os.environ['API_KEY'], "
            "'normal': os.environ['NORMAL']"
            "})); "
            "print(os.environ['API_KEY'], file=sys.stderr)"
        ),
    ]
    assert _run(
        repo_root=repo_root, env_file=env_file, stdout=stdout, stderr=stderr, command=command
    ) == 0
    payload = json.loads(stdout.read_text(encoding="utf-8"))
    assert payload["keys"] == ["API_KEY", "NORMAL"]
    assert "\ufeff" not in "".join(payload["keys"])
    assert payload["api_key"] == "[REDACTED]"
    assert payload["normal"] == "ok"
    assert stderr.read_text(encoding="utf-8") == "[REDACTED]\n"
    assert secret not in stdout.read_text(encoding="utf-8")
    assert secret not in stderr.read_text(encoding="utf-8")
