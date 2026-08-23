"""Stdlib-only bootstrap for the bounded AG-LIVE target.

This wrapper owns Python target/bootstrap observability and the mechanical
sanctioned-packet fallback.  It does not own or duplicate PRODUCT behavior.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

RUNNER_MODULE = "scripts.ag_live_bound_01_bounded_product_runner"
BOOTSTRAP_SCHEMA_VERSION = "ag_live_bound_bootstrap_v1"
BOOTSTRAP_FAILURE_EXIT_CODE = 2
PACKET_WRITE_FAILURE_EXIT_CODE = 3
REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_SAFE_MISSING_MODULE_LENGTH = 160
_SAFE_MODULE_NAME_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z"
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    runner_argv = list(sys.argv[1:] if argv is None else argv)
    output_path = _sanctioned_output_path(runner_argv)
    if output_path is None:
        print(
            "bounded target bootstrap unavailable: sanctioned output path not found",
            file=sys.stderr,
        )
        return PACKET_WRITE_FAILURE_EXIT_CODE

    try:
        runner = importlib.import_module(RUNNER_MODULE)
    except BaseException as exc:
        return _emit_fallback(
            output_path,
            classification="runner_bootstrap_failure",
            safe_phase="runner_import",
            safe_error_type=_safe_error_type(exc),
            missing_module=_safe_missing_module(exc),
            runner_exit_code=None,
            fallback_exit_code=BOOTSTRAP_FAILURE_EXIT_CODE,
        )

    try:
        runner_exit_code = _normalize_exit_code(runner.main(runner_argv))
    except BaseException as exc:
        return _emit_fallback(
            output_path,
            classification="runner_bootstrap_failure",
            safe_phase="runner_entrypoint",
            safe_error_type=_safe_error_type(exc),
            missing_module=_safe_missing_module(exc),
            runner_exit_code=None,
            fallback_exit_code=BOOTSTRAP_FAILURE_EXIT_CODE,
        )

    if output_path.exists():
        return runner_exit_code
    return _emit_fallback(
        output_path,
        classification="runner_exited_without_packet",
        safe_phase="runner_return",
        safe_error_type=None,
        missing_module=None,
        runner_exit_code=runner_exit_code,
        fallback_exit_code=runner_exit_code,
    )


def _emit_fallback(
    output_path: Path,
    *,
    classification: str,
    safe_phase: str,
    safe_error_type: str | None,
    missing_module: str | None,
    runner_exit_code: int | None,
    fallback_exit_code: int,
) -> int:
    if output_path.exists():
        return fallback_exit_code
    packet = {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "classification": classification,
        "safe_phase": safe_phase,
        "safe_error_type": safe_error_type,
        "missing_module": missing_module,
        "interpreter_origin": _interpreter_origin(),
        "runner_exit_code": runner_exit_code,
        "product_result_available": False,
        "raw_private_material_retained": False,
    }
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return fallback_exit_code
        output_path.write_text(
            json.dumps(packet, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        print(
            "bounded target bootstrap unavailable: sanitized packet write failed",
            file=sys.stderr,
        )
        return PACKET_WRITE_FAILURE_EXIT_CODE
    print("wrote sanitized bootstrap terminal packet", file=sys.stderr)
    return fallback_exit_code


def _sanctioned_output_path(runner_argv: Sequence[str]) -> Path | None:
    raw_output = _option_value(runner_argv, "--output")
    if not raw_output:
        return None
    path = Path(raw_output)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()

    repo_output = (Path.cwd() / "output").resolve()
    if path != repo_output and _is_relative_to(path, repo_output):
        return path

    raw_external_root = _option_value(runner_argv, "--external-output-root")
    if not raw_external_root:
        return None
    external_root = Path(raw_external_root)
    if not external_root.is_absolute():
        external_root = Path.cwd() / external_root
    external_root = external_root.resolve()
    if (
        not external_root.is_dir()
        or _is_relative_to(external_root, Path.cwd().resolve())
        or path == external_root
        or not _is_relative_to(path, external_root)
        or not path.parent.is_dir()
    ):
        return None
    return path


def _option_value(argv: Sequence[str], name: str) -> str | None:
    for index, value in enumerate(argv):
        if value == name:
            if index + 1 < len(argv):
                return argv[index + 1]
            return None
        prefix = f"{name}="
        if value.startswith(prefix):
            return value[len(prefix) :]
    return None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _safe_error_type(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name.isidentifier() else "Exception"


def _safe_missing_module(exc: BaseException) -> str | None:
    if not isinstance(exc, ModuleNotFoundError):
        return None
    name = exc.name
    if (
        not isinstance(name, str)
        or len(name) > MAX_SAFE_MISSING_MODULE_LENGTH
        or _SAFE_MODULE_NAME_PATTERN.fullmatch(name) is None
    ):
        return None
    return name


def _interpreter_origin() -> str:
    executable = sys.executable
    if not executable:
        return "non_repo_venv_or_global"
    try:
        Path(executable).resolve().relative_to((REPO_ROOT / ".venv").resolve())
    except (OSError, RuntimeError, ValueError):
        return "non_repo_venv_or_global"
    return "repo_venv"


def _normalize_exit_code(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
