"""Launch one exact owner-specific evaluator with truthful stop attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluation.search_planner_owner_execution_stop_attestation import (
    STARTUP_HANDSHAKE_ENV_VAR,
    STARTUP_HANDSHAKE_TRIGGER_VALUE,
    DerivedExecutionPaths,
    OwnerExecutionStopAttestationError,
    ResultPacketDigestError,
    StopAttestationFacts,
    derive_execution_paths,
    exception_class_code,
    exception_message_sha256,
    load_evaluator_entry_handshake,
    load_validated_result_metadata,
    write_stop_attestation,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    OwnerSpecificAuthorizationError,
    OwnerSpecificLiveAuthorization,
    build_canonical_execute_command,
    load_json_object,
    normalize_repository_relative_path,
)

EVALUATOR_ENTRYPOINT = "scripts/evaluation/run_search_planner_owner_specific_evaluation.py"


class _SilentArgumentParser(argparse.ArgumentParser):
    """Avoid serializing parser details into the bounded operator surface."""

    def error(self, message: str) -> None:
        del message
        raise ValueError("launcher arguments are invalid")


class _LauncherStop(RuntimeError):
    """One known failure mapped to a closed public terminal code."""

    def __init__(
        self,
        code: str,
        cause: BaseException | None = None,
        *,
        safe_exception_class_code: str | None = None,
        safe_exception_message_sha256: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.cause = cause
        self.safe_exception_class_code = safe_exception_class_code
        self.safe_exception_message_sha256 = safe_exception_message_sha256


class _ChildReapingInvariant(RuntimeError):
    """A created child cannot be safely finalized without an exit code."""


@dataclass(frozen=True, slots=True)
class LauncherOutcome:
    """Bounded console facts; private child material never enters this value."""

    facts: StopAttestationFacts
    attestation_relative: str | None
    attestation_sha256: str | None
    process_exit_code: int


@dataclass(frozen=True, slots=True)
class _ChildFinalization:
    """Only bounded child terminal facts; captured streams never enter this value."""

    child_exit_code: int
    reaped: bool
    bounded_failure_code: str | None
    exception_class_code: str
    exception_message_sha256: str | None


def _repository_root() -> Path:
    root = ROOT.resolve()
    if not (root / "scripts" / "evaluation").is_dir():
        raise OSError("repository root is not available")
    return root


def current_repository_sha(*, repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _SilentArgumentParser(
        add_help=False,
        description="Launch the exact owner-specific SearchPlanner evaluator.",
    )
    parser.add_argument("--live-addendum", required=True)
    return parser.parse_args(argv)


def _normalize_addendum_path(
    value: str,
    *,
    repository_root: Path,
) -> str:
    return normalize_repository_relative_path(
        value,
        label="live addendum path",
        repository_root=repository_root,
    )


def _preflight_canonical_command_digest(
    addendum_mapping: Mapping[str, object],
) -> None:
    """Classify a stored command digest mismatch before strict round-trip.

    The authorization owner also rejects this mismatch. This bounded preflight
    preserves the operator-facing distinction without retaining command text.
    """

    identity = addendum_mapping.get("evaluation_identity")
    if not isinstance(identity, Mapping):
        return
    command = identity.get("canonical_operator_command")
    digest = identity.get("canonical_operator_command_digest")
    if (
        isinstance(command, str)
        and isinstance(digest, str)
        and (hashlib.sha256(command.encode("utf-8")).hexdigest() != digest)
    ):
        raise _LauncherStop("CANONICAL_COMMAND_DIGEST_MISMATCH")


def _decode_and_rebuild_canonical_argv(
    authorization: OwnerSpecificLiveAuthorization,
    *,
    repository_sha: str,
    repository_root: Path,
) -> tuple[str, ...]:
    identity = authorization.evaluation_identity
    command = identity.canonical_operator_command
    stored_digest = identity.canonical_operator_command_digest
    if not isinstance(command, str) or (hashlib.sha256(command.encode("utf-8")).hexdigest() != stored_digest):
        raise _LauncherStop("CANONICAL_COMMAND_DIGEST_MISMATCH")
    try:
        decoded = json.loads(command)
    except json.JSONDecodeError as exc:
        raise _LauncherStop("CANONICAL_COMMAND_DECODE_FAILED", exc) from exc
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise _LauncherStop("CANONICAL_ARGV_SHAPE_INVALID")
    canonical_argv = tuple(decoded)
    if not _canonical_argv_shape_is_safe(canonical_argv):
        raise _LauncherStop("CANONICAL_ARGV_SHAPE_INVALID")
    try:
        expected_argv, expected_command, expected_digest = build_canonical_execute_command(
            repository_sha=repository_sha,
            live_addendum_path=identity.live_addendum_path,
            scenario_packet_path=identity.scenario_packet_path,
            output_packet_path=identity.output_packet_path,
            repository_root=repository_root,
        )
    except OwnerSpecificAuthorizationError as exc:
        raise _LauncherStop("CANONICAL_ARGV_REBUILD_MISMATCH", exc) from exc
    if canonical_argv != expected_argv or command != expected_command or stored_digest != expected_digest:
        raise _LauncherStop("CANONICAL_ARGV_REBUILD_MISMATCH")
    return canonical_argv


def _canonical_argv_shape_is_safe(canonical_argv: Sequence[str]) -> bool:
    if len(canonical_argv) != 11 or canonical_argv[0] != EVALUATOR_ENTRYPOINT:
        return False
    expected_options = (
        "--execution-mode",
        "execute",
        "--repository-sha",
        canonical_argv[4],
        "--live-addendum",
        canonical_argv[6],
        "--scenario-packet",
        canonical_argv[8],
        "--output",
        canonical_argv[10],
    )
    if canonical_argv[1:] != expected_options:
        return False
    forbidden_exact = {
        "py",
        "py.exe",
        "python",
        "python.exe",
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "cmd",
        "cmd.exe",
        "invoke-expression",
    }
    return all(
        token.casefold() not in forbidden_exact
        and not any(character in token for character in ("\n", "\r", "|", "&", ";", "`"))
        for token in canonical_argv
    )


def _prepare_paths(
    paths: DerivedExecutionPaths,
) -> None:
    if paths.result_path.exists():
        raise _LauncherStop("RESULT_PATH_ALREADY_EXISTS")
    if paths.startup_path.exists() or paths.attestation_path.exists():
        raise _LauncherStop("ATTESTATION_PATH_ALREADY_EXISTS")
    try:
        paths.startup_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _LauncherStop("HANDSHAKE_PATH_REJECTED", exc) from exc


def _child_environment() -> dict[str, str]:
    """Preserve inherited execution custody while adding one private marker."""

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment[STARTUP_HANDSHAKE_ENV_VAR] = STARTUP_HANDSHAKE_TRIGGER_VALUE
    return environment


def _finalized_child_exit_code(child: subprocess.Popen[str]) -> int:
    """Require the process API to confirm a terminal, reaped child."""

    child_exit_code = child.returncode
    if isinstance(child_exit_code, bool) or not isinstance(child_exit_code, int):
        raise _ChildReapingInvariant("created child did not expose one terminal exit code")
    return child_exit_code


def _reap_child_after_interruption(
    child: subprocess.Popen[str],
    *,
    bounded_failure_code: str,
    exception_class: str,
    exception_digest: str | None,
    kill_unconditionally: bool,
) -> _ChildFinalization:
    """Terminate when needed, reap exactly once, and discard both stream values."""

    if kill_unconditionally or child.poll() is None:
        child.kill()
    child.communicate()
    return _ChildFinalization(
        child_exit_code=_finalized_child_exit_code(child),
        reaped=True,
        bounded_failure_code=bounded_failure_code,
        exception_class_code=exception_class,
        exception_message_sha256=exception_digest,
    )


def _communicate_and_reap_authorized_child(
    child: subprocess.Popen[str],
    *,
    remaining_seconds: float,
) -> _ChildFinalization:
    """Wait within the authorized remainder or kill/reap before any terminal write."""

    if not math.isfinite(remaining_seconds) or remaining_seconds <= 0:
        return _reap_child_after_interruption(
            child,
            bounded_failure_code="CHILD_PROCESS_TIMEOUT",
            exception_class="NONE",
            exception_digest=None,
            kill_unconditionally=True,
        )
    try:
        child.communicate(timeout=remaining_seconds)
    except subprocess.TimeoutExpired as exc:
        return _reap_child_after_interruption(
            child,
            bounded_failure_code="CHILD_PROCESS_TIMEOUT",
            exception_class=exception_class_code(exc),
            exception_digest=exception_message_sha256(exc),
            kill_unconditionally=True,
        )
    except Exception as exc:
        return _reap_child_after_interruption(
            child,
            bounded_failure_code="CHILD_PROCESS_COMMUNICATION_FAILED",
            exception_class=exception_class_code(exc),
            exception_digest=exception_message_sha256(exc),
            kill_unconditionally=False,
        )
    if child.returncode is None:
        invariant_error = ValueError("child communicate returned without one terminal exit code")
        return _reap_child_after_interruption(
            child,
            bounded_failure_code="CHILD_PROCESS_COMMUNICATION_FAILED",
            exception_class=exception_class_code(invariant_error),
            exception_digest=exception_message_sha256(invariant_error),
            kill_unconditionally=False,
        )
    return _ChildFinalization(
        child_exit_code=_finalized_child_exit_code(child),
        reaped=True,
        bounded_failure_code=None,
        exception_class_code="NONE",
        exception_message_sha256=None,
    )


def _record_failure(
    facts: StopAttestationFacts,
    *,
    code: str,
    terminal_status: str,
    exc: BaseException | None,
    safe_exception_class_code: str | None = None,
    safe_exception_message_sha256: str | None = None,
) -> None:
    facts.bounded_failure_code = code
    facts.terminal_status = terminal_status
    facts.exception_class_code = (
        exception_class_code(exc) if safe_exception_class_code is None else safe_exception_class_code
    )
    facts.exception_message_sha256 = (
        exception_message_sha256(exc) if safe_exception_class_code is None else safe_exception_message_sha256
    )


def _terminal_status_for_failure(
    facts: StopAttestationFacts,
    *,
    code: str,
) -> str:
    if code in {
        "RESULT_PACKET_VALIDATION_FAILED",
        "RESULT_PACKET_DIGEST_FAILED",
    }:
        return "STOPPED_DURING_RESULT_VALIDATION"
    if code in {
        "CHILD_PROCESS_NONZERO_EXIT",
        "CHILD_PROCESS_TIMEOUT",
        "CHILD_PROCESS_COMMUNICATION_FAILED",
    }:
        return "STOPPED_AFTER_CHILD_EXIT"
    if not facts.child_process_created:
        return "STOPPED_PRE_CHILD"
    if facts.evaluator_entry_posture == "UNKNOWN":
        return "STOPPED_PRE_EVALUATOR_ENTRY"
    return "STOPPED_AFTER_EVALUATOR_ENTRY"


def _observe_startup_handshake(
    facts: StopAttestationFacts,
    *,
    paths: DerivedExecutionPaths,
    repository_root: Path,
    strict: bool,
) -> None:
    if not paths.startup_path.is_file():
        return
    try:
        handshake = load_evaluator_entry_handshake(
            paths.startup_path,
            repository_root=repository_root,
        )
    except (
        OwnerExecutionStopAttestationError,
        OwnerSpecificAuthorizationError,
    ) as exc:
        if not strict:
            return
        raise _LauncherStop("EVALUATOR_HANDSHAKE_INVALID", exc) from exc
    except Exception:
        if strict:
            raise
        return
    facts.note_evaluator_entry(str(handshake["stage"]))


def _demote_exact_result_metadata(facts: StopAttestationFacts) -> None:
    """Keep a failed final write from exposing exact successful-result posture."""

    if facts.manifest_consumption_posture != "EXACT" and facts.cost_posture != "EXACT":
        return
    facts.result_packet_sha256 = None
    facts.broker_startup_posture = "UNKNOWN"
    facts.planner_calls = None
    facts.primary_judge_calls = None
    facts.adversarial_judge_calls = None
    facts.total_broker_calls = None
    facts.observed_cost_usd = None
    if facts.evaluator_entry_posture == "TRUE":
        facts.manifest_consumption_posture = "UNKNOWN_AFTER_EVALUATOR_ENTRY"
        facts.cost_posture = "UNKNOWN_AFTER_EVALUATOR_ENTRY"
    else:
        facts.manifest_consumption_posture = "UNKNOWN_AFTER_CHILD_CREATION"
        facts.cost_posture = "UNKNOWN_AFTER_CHILD_CREATION"


def _write_final_attestation(
    facts: StopAttestationFacts,
    *,
    paths: DerivedExecutionPaths | None,
    repository_root: Path | None,
    child_reaped: bool,
) -> tuple[str | None, str | None, bool]:
    if paths is None or repository_root is None:
        return None, None, False
    if facts.child_process_created and (not child_reaped or facts.child_exit_code is None):
        return None, None, False
    if facts.bounded_failure_code == "ATTESTATION_PATH_ALREADY_EXISTS":
        return paths.attestation_relative, None, False
    try:
        facts.operator_stage = "ATTESTATION_WRITE"
        packet = write_stop_attestation(
            paths.attestation_path,
            repository_root=repository_root,
            facts=facts,
        )
    except Exception as exc:
        _demote_exact_result_metadata(facts)
        facts.terminal_status = "STOPPED_DURING_ATTESTATION_WRITE"
        facts.bounded_failure_code = "ATTESTATION_WRITE_FAILED"
        facts.exception_class_code = exception_class_code(exc)
        facts.exception_message_sha256 = exception_message_sha256(exc)
        return paths.attestation_relative, None, False
    return paths.attestation_relative, str(packet["attestation_sha256"]), True


def execute_launcher(
    argv: Sequence[str] | None = None,
) -> LauncherOutcome:
    """Run one bounded child process and produce truthful safe terminal facts."""

    launcher_started_at = time.monotonic()
    facts = StopAttestationFacts()
    repository_root: Path | None = None
    paths: DerivedExecutionPaths | None = None
    child: subprocess.Popen[str] | None = None
    child_finalization: _ChildFinalization | None = None
    try:
        try:
            repository_root = _repository_root()
        except OSError as exc:
            raise _LauncherStop("REPOSITORY_ROOT_RESOLUTION_FAILED", exc) from exc
        facts.operator_stage = "REPOSITORY_ROOT_RESOLVED"
        args = _parse_args(argv)
        try:
            addendum_relative = _normalize_addendum_path(
                args.live_addendum,
                repository_root=repository_root,
            )
        except OwnerSpecificAuthorizationError as exc:
            raise _LauncherStop("LIVE_ADDENDUM_PATH_REJECTED", exc) from exc
        facts.operator_stage = "LIVE_ADDENDUM_PATH_NORMALIZED"
        try:
            addendum_mapping = load_json_object(repository_root / addendum_relative)
        except OwnerSpecificAuthorizationError as exc:
            raise _LauncherStop("LIVE_ADDENDUM_READ_FAILED", exc) from exc
        facts.operator_stage = "LIVE_ADDENDUM_LOADED"
        _preflight_canonical_command_digest(addendum_mapping)
        try:
            authorization = OwnerSpecificLiveAuthorization.from_mapping(addendum_mapping)
            if authorization.evaluation_identity.live_addendum_path != addendum_relative:
                raise OwnerSpecificAuthorizationError("authorization live addendum path is not exact")
        except OwnerSpecificAuthorizationError as exc:
            raise _LauncherStop("AUTHORIZATION_VALIDATION_FAILED", exc) from exc
        facts.authorization_sha256 = authorization.authorization_sha256
        facts.canonical_command_digest = authorization.evaluation_identity.canonical_operator_command_digest
        try:
            paths = derive_execution_paths(
                authorization,
                repository_root=repository_root,
            )
            paths.attestation_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
        except (OwnerExecutionStopAttestationError, OSError) as exc:
            raise _LauncherStop("HANDSHAKE_PATH_REJECTED", exc) from exc
        facts.operator_stage = "AUTHORIZATION_ROUND_TRIPPED"
        try:
            repository_sha = current_repository_sha(repository_root=repository_root)
        except (OSError, subprocess.SubprocessError) as exc:
            raise _LauncherStop("REPOSITORY_ROOT_RESOLUTION_FAILED", exc) from exc
        facts.repository_sha = repository_sha
        if repository_sha != authorization.evaluation_identity.repository_sha:
            raise _LauncherStop("REPOSITORY_SHA_MISMATCH")
        facts.operator_stage = "REPOSITORY_SHA_VERIFIED"
        canonical_argv = _decode_and_rebuild_canonical_argv(
            authorization,
            repository_sha=repository_sha,
            repository_root=repository_root,
        )
        facts.operator_stage = "CANONICAL_COMMAND_VERIFIED"
        try:
            _prepare_paths(paths)
        except _LauncherStop:
            raise
        except (
            OwnerExecutionStopAttestationError,
            OwnerSpecificAuthorizationError,
        ) as exc:
            raise _LauncherStop("HANDSHAKE_PATH_REJECTED", exc) from exc
        facts.operator_stage = "OUTPUT_PATHS_PREPARED"
        try:
            child = subprocess.Popen(
                [sys.executable, *canonical_argv],
                cwd=repository_root,
                env=_child_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise _LauncherStop("CHILD_PROCESS_CREATE_FAILED", exc) from exc
        facts.note_child_created()
        facts.captured_stdout = True
        facts.captured_stderr = True
        facts.operator_stage = "CHILD_PROCESS_CREATED"
        try:
            deadline = launcher_started_at + authorization.whole_evaluation_caps.maximum_wall_clock_seconds
            remaining_seconds = deadline - time.monotonic()
        except Exception:
            remaining_seconds = 0.0
        child_finalization = _communicate_and_reap_authorized_child(
            child,
            remaining_seconds=remaining_seconds,
        )
        facts.child_exit_code = child_finalization.child_exit_code
        facts.operator_stage = "CHILD_EXIT_RECORDED"
        if child_finalization.bounded_failure_code is not None:
            _observe_startup_handshake(
                facts,
                paths=paths,
                repository_root=repository_root,
                strict=False,
            )
            raise _LauncherStop(
                child_finalization.bounded_failure_code,
                safe_exception_class_code=(child_finalization.exception_class_code),
                safe_exception_message_sha256=(child_finalization.exception_message_sha256),
            )
        if facts.child_exit_code != 0:
            _observe_startup_handshake(
                facts,
                paths=paths,
                repository_root=repository_root,
                strict=False,
            )
            raise _LauncherStop("CHILD_PROCESS_NONZERO_EXIT")
        _observe_startup_handshake(
            facts,
            paths=paths,
            repository_root=repository_root,
            strict=True,
        )
        if facts.evaluator_entry_posture == "UNKNOWN":
            raise _LauncherStop("EVALUATOR_ENTRY_UNATTESTED")
        if not paths.result_path.is_file():
            raise _LauncherStop("RESULT_PACKET_MISSING")
        facts.note_result_packet_observed()
        try:
            result_digest, metadata = load_validated_result_metadata(
                paths.result_path,
                authorization=authorization,
                repository_sha=repository_sha,
            )
        except ResultPacketDigestError as exc:
            raise _LauncherStop("RESULT_PACKET_DIGEST_FAILED", exc) from exc
        except OwnerExecutionStopAttestationError as exc:
            raise _LauncherStop("RESULT_PACKET_VALIDATION_FAILED", exc) from exc
        facts.note_exact_result(
            result_packet_sha256=result_digest,
            metadata=metadata,
        )
        facts.operator_stage = "RESULT_PACKET_VALIDATED"
        facts.terminal_status = "COMPLETE"
        facts.bounded_failure_code = "NONE"
        facts.exception_class_code = "NONE"
        facts.exception_message_sha256 = None
    except _ChildReapingInvariant:
        raise
    except _LauncherStop as stop:
        terminal_status = _terminal_status_for_failure(
            facts,
            code=stop.code,
        )
        _record_failure(
            facts,
            code=stop.code,
            terminal_status=terminal_status,
            exc=stop.cause,
            safe_exception_class_code=stop.safe_exception_class_code,
            safe_exception_message_sha256=stop.safe_exception_message_sha256,
        )
    except Exception as exc:
        terminal_status = _terminal_status_for_failure(
            facts,
            code="UNEXPECTED_OPERATOR_EXCEPTION",
        )
        _record_failure(
            facts,
            code="UNEXPECTED_OPERATOR_EXCEPTION",
            terminal_status=terminal_status,
            exc=exc,
        )
    finally:
        facts.elapsed_milliseconds = max(
            0,
            int((time.monotonic() - launcher_started_at) * 1000),
        )
    child_reaped = not facts.child_process_created or (
        child_finalization is not None and child_finalization.reaped and facts.child_exit_code is not None
    )
    if not child_reaped:
        raise _ChildReapingInvariant("launcher cannot return before a created child is reaped")
    relative, digest, written = _write_final_attestation(
        facts,
        paths=paths,
        repository_root=repository_root,
        child_reaped=child_reaped,
    )
    process_exit_code = 0 if facts.terminal_status == "COMPLETE" and written else 2
    return LauncherOutcome(
        facts=facts,
        attestation_relative=relative,
        attestation_sha256=digest,
        process_exit_code=process_exit_code,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Print only the bounded launcher terminal projection."""

    outcome = execute_launcher(argv)
    print(f"terminal_status={outcome.facts.terminal_status}")
    print(f"bounded_failure_code={outcome.facts.bounded_failure_code}")
    print("stop_attestation_path=" + (outcome.attestation_relative or "NONE"))
    print("stop_attestation_sha256=" + (outcome.attestation_sha256 or "NONE"))
    print(f"process_exit_code={outcome.process_exit_code}")
    return outcome.process_exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EVALUATOR_ENTRYPOINT",
    "LauncherOutcome",
    "current_repository_sha",
    "execute_launcher",
    "main",
]
