from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

from scripts import request_provider_proxy_broker as broker_client
from scripts.evaluation import (
    launch_search_planner_owner_specific_evaluation as launcher,
)
from scripts.evaluation import (
    search_planner_owner_execution_stop_attestation as attestation,
)
from scripts.evaluation.search_planner_owner_specific_orchestration import (
    execute_owner_specific_evaluation,
)
from tests.helpers.search_planner_owner_specific_fakes import (
    FakeOwnerSpecificBrokerFactory,
    authorization_bundle,
)

REPOSITORY_SHA = "".join(("3a76a3a2", "4efef5ee", "4bec2d43", "e301463b", "671f0d80"))


def _launcher_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "repository"
    (root / "scripts" / "evaluation").mkdir(parents=True)
    authorization, scenario, argv = authorization_bundle(
        repository_root=root,
        repository_sha=REPOSITORY_SHA,
    )
    addendum_path = root / authorization.evaluation_identity.live_addendum_path
    scenario_path = root / authorization.evaluation_identity.scenario_packet_path
    addendum_path.parent.mkdir(parents=True, exist_ok=True)
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    addendum_path.write_text(
        json.dumps(authorization.to_packet()),
        encoding="utf-8",
    )
    scenario_path.write_text(
        json.dumps(scenario.to_packet()),
        encoding="utf-8",
    )
    monkeypatch.setattr(launcher, "ROOT", root)
    monkeypatch.setattr(
        launcher,
        "current_repository_sha",
        lambda *, repository_root: REPOSITORY_SHA,
    )
    return root, authorization, scenario, argv


def _replace_canonical_command(
    payload: dict[str, Any],
    command: str,
) -> None:
    identity = payload["evaluation_identity"]
    assert isinstance(identity, dict)
    identity["canonical_operator_command"] = command
    identity["canonical_operator_command_digest"] = hashlib.sha256(command.encode("utf-8")).hexdigest()


def _raise(exception: BaseException):
    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise exception

    return fail


class _FakeChildProcess:
    def __init__(
        self,
        *,
        exit_code: int,
        stdout: str,
        stderr: str,
        on_communicate: Callable[[], None] | None,
        initial_exception: BaseException | None = None,
        on_reap_communicate: Callable[[], None] | None = None,
        reap_exception: BaseException | None = None,
        poll_exit_code: int | None = None,
        normal_returncode: bool = True,
        reap_returncode: bool = True,
    ) -> None:
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        self._on_communicate = on_communicate
        self._initial_exception = initial_exception
        self._on_reap_communicate = on_reap_communicate
        self._reap_exception = reap_exception
        self._poll_exit_code = poll_exit_code
        self._normal_returncode = normal_returncode
        self._reap_returncode = reap_returncode
        self._active = True
        self._initial_communicated = False
        self.reaped = False
        self.kill_calls = 0
        self.communicate_timeouts: list[float | None] = []
        self.returncode: int | None = None

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        self.communicate_timeouts.append(timeout)
        if timeout is not None:
            if self._initial_communicated:
                raise AssertionError("fake child received more than one initial communicate call")
            self._initial_communicated = True
            if self._on_communicate is not None:
                self._on_communicate()
            if self._initial_exception is not None:
                raise self._initial_exception
            if self._normal_returncode:
                self.returncode = self._exit_code
                self._active = False
                self.reaped = True
            return self._stdout, self._stderr
        if self._active and self.kill_calls == 0:
            raise AssertionError("launcher attempted an unbounded wait for an active child")
        if self._on_reap_communicate is not None:
            self._on_reap_communicate()
        if self._reap_exception is not None:
            raise self._reap_exception
        if self._reap_returncode:
            self.returncode = self._exit_code
            self._active = False
            self.reaped = True
        return self._stdout, self._stderr

    def poll(self) -> int | None:
        if self._poll_exit_code is not None:
            self.returncode = self._poll_exit_code
            self._active = False
        return self.returncode

    def kill(self) -> None:
        self.kill_calls += 1


def _fake_child(
    *,
    root: Path,
    argv: tuple[str, ...],
    exit_code: int = 0,
    write_marker: bool = True,
    stdout: str = "fictional-private-stdout-sentinel",
    stderr: str = "fictional-private-stderr-sentinel",
    on_communicate: Callable[[], None] | None = None,
    initial_exception: BaseException | None = None,
    on_reap_communicate: Callable[[], None] | None = None,
    reap_exception: BaseException | None = None,
    poll_exit_code: int | None = None,
    normal_returncode: bool = True,
    reap_returncode: bool = True,
) -> tuple[Callable[..., _FakeChildProcess], dict[str, Any]]:
    observed: dict[str, Any] = {}

    def popen(command: list[str], **kwargs: Any) -> _FakeChildProcess:
        observed["command"] = command
        observed["kwargs"] = kwargs
        assert command == [sys.executable, *argv]
        assert kwargs["cwd"] == root
        assert kwargs["stdout"] is subprocess.PIPE
        assert kwargs["stderr"] is subprocess.PIPE
        assert kwargs["text"] is True
        environment = kwargs["env"]
        assert "PYTHONPATH" not in environment
        assert environment[attestation.STARTUP_HANDSHAKE_ENV_VAR] == attestation.STARTUP_HANDSHAKE_TRIGGER_VALUE
        if write_marker:
            attestation.write_evaluator_entry_handshake(
                argv[argv.index("--output") + 1],
                repository_root=root,
            )
        child = _FakeChildProcess(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            on_communicate=on_communicate,
            initial_exception=initial_exception,
            on_reap_communicate=on_reap_communicate,
            reap_exception=reap_exception,
            poll_exit_code=poll_exit_code,
            normal_returncode=normal_returncode,
            reap_returncode=reap_returncode,
        )
        observed["child"] = child
        return child

    return popen, observed


def test_launcher_is_cwd_independent_and_does_not_need_operator_pythonpath(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_run, observed = _fake_child(root=root, argv=argv)
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_run)
    monkeypatch.setenv("PYTHONPATH", "operator-supplied-sentinel")
    monkeypatch.chdir(tmp_path)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.process_exit_code == 2
    assert outcome.facts.bounded_failure_code == "RESULT_PACKET_MISSING"
    assert outcome.facts.child_process_created is True
    assert outcome.facts.evaluator_entry_posture == "TRUE"
    assert outcome.facts.manifest_consumption_posture == ("UNKNOWN_AFTER_EVALUATOR_ENTRY")
    assert outcome.facts.planner_calls is None
    assert outcome.facts.observed_cost_usd is None
    assert (
        observed["kwargs"]["env"][attestation.STARTUP_HANDSHAKE_ENV_VAR] == attestation.STARTUP_HANDSHAKE_TRIGGER_VALUE
    )
    assert outcome.attestation_relative == ("output/local/owner-specific-result.json.stop-attestation.json")
    assert observed["command"][0] == sys.executable
    assert not {token.casefold() for token in observed["command"][1:]}.intersection(
        {
            "py",
            "python",
            "powershell",
            "pwsh",
            "invoke-expression",
        }
    )
    packet = attestation.load_json_object(root / outcome.attestation_relative)
    attestation.validate_stop_attestation_packet(packet)
    rendered = json.dumps(packet, sort_keys=True)
    assert "fictional-private-stdout-sentinel" not in rendered
    assert "fictional-private-stderr-sentinel" not in rendered


def test_digest_mismatch_stops_before_child_and_records_exact_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)
    addendum_path = root / authorization.evaluation_identity.live_addendum_path
    payload = json.loads(addendum_path.read_text(encoding="utf-8"))
    payload["evaluation_identity"]["canonical_operator_command_digest"] = "0" * 64
    addendum_path.write_text(json.dumps(payload), encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == ("CANONICAL_COMMAND_DIGEST_MISMATCH")
    assert outcome.facts.child_process_created is False
    assert outcome.facts.evaluator_entry_posture == "FALSE"
    assert outcome.facts.planner_calls == 0
    assert outcome.facts.observed_cost_usd == "0"
    assert calls == []


@pytest.mark.parametrize(
    ("command", "expected_code"),
    (
        ("{", "CANONICAL_COMMAND_DECODE_FAILED"),
        (json.dumps(["py"]), "CANONICAL_ARGV_SHAPE_INVALID"),
    ),
)
def test_malformed_or_unsafe_canonical_command_stops_before_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    expected_code: str,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)
    addendum_path = root / authorization.evaluation_identity.live_addendum_path
    payload = json.loads(addendum_path.read_text(encoding="utf-8"))
    _replace_canonical_command(payload, command)
    addendum_path.write_text(json.dumps(payload), encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == expected_code
    assert outcome.facts.child_process_created is False
    assert outcome.facts.evaluator_entry_posture == "FALSE"
    assert outcome.facts.exception_class_code in {"JSON_DECODE_ERROR", "NONE"}
    assert calls == []


def test_rebuilt_canonical_command_must_match_exact_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    addendum_path = root / authorization.evaluation_identity.live_addendum_path
    payload = json.loads(addendum_path.read_text(encoding="utf-8"))
    altered_argv = list(argv)
    altered_argv[6] = "authorizations/not-the-licensed-addendum.json"
    _replace_canonical_command(
        payload,
        json.dumps(altered_argv, separators=(",", ":")),
    )
    addendum_path.write_text(json.dumps(payload), encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "CANONICAL_ARGV_REBUILD_MISMATCH"
    assert outcome.facts.child_process_created is False
    assert outcome.facts.evaluator_entry_posture == "FALSE"
    assert calls == []


@pytest.mark.parametrize(
    "suffix",
    (".startup.json", ".stop-attestation.json"),
)
def test_existing_derived_attestation_target_blocks_before_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)
    result_path = root / authorization.evaluation_identity.output_packet_path
    target = Path(str(result_path) + suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("sentinel", encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "ATTESTATION_PATH_ALREADY_EXISTS"
    assert outcome.facts.child_process_created is False
    assert target.read_text(encoding="utf-8") == "sentinel"
    assert calls == []


def test_existing_result_blocks_before_child_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)
    result_path = root / authorization.evaluation_identity.output_packet_path
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("{}", encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "RESULT_PATH_ALREADY_EXISTS"
    assert outcome.facts.child_process_created is False
    assert calls == []
    assert result_path.read_text(encoding="utf-8") == "{}"


def test_child_without_marker_preserves_unknown_call_and_cost_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_run, _ = _fake_child(
        root=root,
        argv=argv,
        write_marker=False,
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_run)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "EVALUATOR_ENTRY_UNATTESTED"
    assert outcome.facts.child_process_created is True
    assert outcome.facts.evaluator_entry_posture == "UNKNOWN"
    assert outcome.facts.planner_calls is None
    assert outcome.facts.total_broker_calls is None
    assert outcome.facts.observed_cost_usd is None


def test_nonzero_child_with_valid_marker_preserves_entry_but_not_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_run, _ = _fake_child(root=root, argv=argv, exit_code=7)
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_run)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "CHILD_PROCESS_NONZERO_EXIT"
    assert outcome.facts.child_exit_code == 7
    assert outcome.facts.evaluator_entry_posture == "TRUE"
    assert outcome.facts.planner_calls is None
    assert outcome.facts.observed_cost_usd is None


def test_validated_normal_result_is_projected_as_exact_without_live_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, scenario, argv = _launcher_fixture(tmp_path, monkeypatch)
    result_path = root / authorization.evaluation_identity.output_packet_path
    monkeypatch.setenv(broker_client.TOKEN_ENV_VAR, "synthetic-test-session")
    packet = execute_owner_specific_evaluation(
        authorization=authorization,
        scenario_packet=scenario,
        repository_sha=REPOSITORY_SHA,
        live_addendum_path=authorization.evaluation_identity.live_addendum_path,
        scenario_packet_path=authorization.evaluation_identity.scenario_packet_path,
        output_packet_path=authorization.evaluation_identity.output_packet_path,
        actual_argv=argv,
        repository_root=root,
        transport_factory=FakeOwnerSpecificBrokerFactory(),
    )
    rendered_result = result_path.read_text(encoding="utf-8")
    result_path.unlink()

    def write_result() -> None:
        result_path.write_text(rendered_result, encoding="utf-8")

    fake_popen, _ = _fake_child(
        root=root,
        argv=argv,
        on_communicate=write_result,
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.process_exit_code == 0
    assert outcome.facts.terminal_status == "COMPLETE"
    assert outcome.facts.bounded_failure_code == "NONE"
    assert outcome.facts.result_packet_created is True
    assert outcome.facts.manifest_consumption_posture == "EXACT"
    assert outcome.facts.cost_posture == "EXACT"
    assert outcome.facts.planner_calls == 2
    assert outcome.facts.primary_judge_calls == 2
    assert outcome.facts.adversarial_judge_calls == 2
    assert outcome.facts.total_broker_calls == 6
    assert outcome.facts.observed_cost_usd == packet["budget_and_cap_consumption"]["total_observed_cost_usd"]


def test_unexpected_post_child_failure_never_collapses_to_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_run, _ = _fake_child(root=root, argv=argv)
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_run)
    private_sentinel = "fictional-private-marker-validation-sentinel"

    def fail_marker(*args, **kwargs):
        raise RuntimeError(private_sentinel)

    monkeypatch.setattr(launcher, "load_evaluator_entry_handshake", fail_marker)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "UNEXPECTED_OPERATOR_EXCEPTION"
    assert outcome.facts.child_process_created is True
    assert outcome.facts.evaluator_entry_posture == "UNKNOWN"
    assert outcome.facts.planner_calls is None
    assert outcome.facts.observed_cost_usd is None
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    assert private_sentinel not in json.dumps(packet, sort_keys=True)


def test_communicate_failure_after_child_creation_preserves_unknown_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    private_sentinel = "fictional-private-communicate-sentinel"
    fake_popen, observed = _fake_child(
        root=root,
        argv=argv,
        write_marker=False,
        on_communicate=_raise(RuntimeError(private_sentinel)),
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    child = observed["child"]
    assert outcome.facts.bounded_failure_code == "CHILD_PROCESS_COMMUNICATION_FAILED"
    assert outcome.facts.terminal_status == "STOPPED_AFTER_CHILD_EXIT"
    assert outcome.facts.operator_stage == "ATTESTATION_WRITE"
    assert outcome.facts.child_process_created is True
    assert outcome.facts.child_exit_code == 0
    assert outcome.facts.evaluator_entry_posture == "UNKNOWN"
    assert outcome.facts.manifest_consumption_posture == "UNKNOWN_AFTER_CHILD_CREATION"
    assert outcome.facts.cost_posture == "UNKNOWN_AFTER_CHILD_CREATION"
    assert outcome.facts.planner_calls is None
    assert outcome.facts.total_broker_calls is None
    assert outcome.facts.observed_cost_usd is None
    assert child.kill_calls == 1
    assert child.reaped is True
    assert child.communicate_timeouts[0] is not None
    assert child.communicate_timeouts[1] is None
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    assert private_sentinel not in json.dumps(packet, sort_keys=True)


@pytest.mark.parametrize(
    ("handshake_state", "expected_posture"),
    (
        ("valid", "TRUE"),
        ("missing", "UNKNOWN"),
        ("invalid", "UNKNOWN"),
    ),
)
def test_timeout_kills_reaps_and_never_validates_a_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    handshake_state: str,
    expected_posture: str,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    result_path = root / authorization.evaluation_identity.output_packet_path
    private_result = "fictional-private-timeout-result-sentinel"
    private_stdout = "fictional-private-timeout-stdout-sentinel"
    private_stderr = "fictional-private-timeout-stderr-sentinel"

    def write_post_child_material() -> None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps({"fixture": private_result}),
            encoding="utf-8",
        )
        if handshake_state == "invalid":
            startup_path = root / (authorization.evaluation_identity.output_packet_path + ".startup.json")
            startup_path.write_text(
                '{"fixture":"fictional-private-timeout-handshake-sentinel"}',
                encoding="utf-8",
            )

    fake_popen, observed = _fake_child(
        root=root,
        argv=argv,
        exit_code=-9,
        write_marker=handshake_state == "valid",
        stdout=private_stdout,
        stderr=private_stderr,
        on_communicate=write_post_child_material,
        initial_exception=subprocess.TimeoutExpired("synthetic-child", 1),
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        launcher,
        "load_validated_result_metadata",
        _raise(AssertionError("timeout path attempted result validation")),
    )
    production_writer = launcher.write_stop_attestation
    writer_calls: list[object] = []

    def checked_writer(*args: Any, **kwargs: Any) -> dict[str, Any]:
        child = observed["child"]
        facts = kwargs["facts"]
        assert child.reaped is True
        assert child.returncode is not None
        assert facts.child_exit_code == child.returncode
        writer_calls.append((args, kwargs))
        return production_writer(*args, **kwargs)

    monkeypatch.setattr(launcher, "write_stop_attestation", checked_writer)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    child = observed["child"]
    assert outcome.facts.bounded_failure_code == "CHILD_PROCESS_TIMEOUT"
    assert outcome.facts.terminal_status == "STOPPED_AFTER_CHILD_EXIT"
    assert outcome.facts.child_exit_code == -9
    assert outcome.facts.evaluator_entry_posture == expected_posture
    assert outcome.facts.result_packet_created is False
    assert outcome.facts.result_packet_sha256 is None
    assert outcome.facts.manifest_consumption_posture == (
        "UNKNOWN_AFTER_EVALUATOR_ENTRY" if expected_posture == "TRUE" else "UNKNOWN_AFTER_CHILD_CREATION"
    )
    assert outcome.facts.cost_posture == outcome.facts.manifest_consumption_posture
    assert outcome.facts.total_broker_calls is None
    assert outcome.facts.observed_cost_usd is None
    assert child.kill_calls == 1
    assert child.reaped is True
    assert child.communicate_timeouts[0] is not None
    assert child.communicate_timeouts[1] is None
    assert len(writer_calls) == 1
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    rendered = "\n".join(
        (
            json.dumps(packet, sort_keys=True),
            repr(outcome),
            capsys.readouterr().out,
        )
    )
    assert private_result not in rendered
    assert private_stdout not in rendered
    assert private_stderr not in rendered


@pytest.mark.parametrize(
    ("handshake_state", "expected_posture"),
    (
        ("valid", "TRUE"),
        ("missing", "UNKNOWN"),
        ("invalid", "UNKNOWN"),
    ),
)
def test_communication_failure_kills_reaps_and_keeps_private_data_out(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    handshake_state: str,
    expected_posture: str,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    private_exception = "fictional-private-communication-exception-sentinel"
    private_stdout = "fictional-private-communication-stdout-sentinel"
    private_stderr = "fictional-private-communication-stderr-sentinel"

    def write_invalid_marker() -> None:
        if handshake_state == "invalid":
            startup_path = root / (authorization.evaluation_identity.output_packet_path + ".startup.json")
            startup_path.write_text(
                '{"fixture":"fictional-private-communication-handshake-sentinel"}',
                encoding="utf-8",
            )

    fake_popen, observed = _fake_child(
        root=root,
        argv=argv,
        exit_code=-9,
        write_marker=handshake_state == "valid",
        stdout=private_stdout,
        stderr=private_stderr,
        on_communicate=write_invalid_marker,
        initial_exception=RuntimeError(private_exception),
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    child = observed["child"]
    assert outcome.facts.bounded_failure_code == "CHILD_PROCESS_COMMUNICATION_FAILED"
    assert outcome.facts.terminal_status == "STOPPED_AFTER_CHILD_EXIT"
    assert outcome.facts.child_exit_code == -9
    assert outcome.facts.evaluator_entry_posture == expected_posture
    assert outcome.facts.planner_calls is None
    assert outcome.facts.total_broker_calls is None
    assert outcome.facts.observed_cost_usd is None
    assert child.kill_calls == 1
    assert child.reaped is True
    assert child.communicate_timeouts[0] is not None
    assert child.communicate_timeouts[1] is None
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    rendered = json.dumps(packet, sort_keys=True) + repr(outcome)
    assert private_exception not in rendered
    assert private_stdout not in rendered
    assert private_stderr not in rendered


def test_communication_failure_reaps_an_already_exited_child_without_killing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_popen, observed = _fake_child(
        root=root,
        argv=argv,
        exit_code=7,
        write_marker=False,
        initial_exception=RuntimeError("fictional-private-poll-sentinel"),
        poll_exit_code=7,
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    child = observed["child"]
    assert outcome.facts.bounded_failure_code == "CHILD_PROCESS_COMMUNICATION_FAILED"
    assert outcome.facts.child_exit_code == 7
    assert child.kill_calls == 0
    assert child.reaped is True
    assert child.communicate_timeouts[1] is None


def test_remaining_authorization_budget_bounds_the_first_child_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    assert authorization.whole_evaluation_caps.maximum_wall_clock_seconds == 300
    fake_popen, observed = _fake_child(root=root, argv=argv)
    monotonic_values = iter((0.0, 17.0))

    def controlled_monotonic() -> float:
        return next(monotonic_values, 17.0)

    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(launcher.time, "monotonic", controlled_monotonic)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "RESULT_PACKET_MISSING"
    assert observed["child"].communicate_timeouts == [283.0]


def test_consumed_authorization_budget_kills_and_reaps_without_an_initial_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_popen, observed = _fake_child(root=root, argv=argv, exit_code=-9)
    monotonic_values = iter((0.0, 300.0))

    def controlled_monotonic() -> float:
        return next(monotonic_values, 300.0)

    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(launcher.time, "monotonic", controlled_monotonic)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    child = observed["child"]
    assert outcome.facts.bounded_failure_code == "CHILD_PROCESS_TIMEOUT"
    assert outcome.facts.terminal_status == "STOPPED_AFTER_CHILD_EXIT"
    assert child.kill_calls == 1
    assert child.reaped is True
    assert child.communicate_timeouts == [None]


def test_unreaped_child_never_attempts_final_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_popen, observed = _fake_child(
        root=root,
        argv=argv,
        write_marker=False,
        normal_returncode=False,
        reap_returncode=False,
    )
    writer_calls: list[object] = []
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        launcher,
        "write_stop_attestation",
        lambda *args, **kwargs: writer_calls.append((args, kwargs)),
    )

    with pytest.raises(launcher._ChildReapingInvariant):
        launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    child = observed["child"]
    assert child.kill_calls == 1
    assert child.reaped is False
    assert child.returncode is None
    assert writer_calls == []


def test_console_discards_fake_streams(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_run, _ = _fake_child(root=root, argv=argv)
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_run)

    assert launcher.main(("--live-addendum", authorization.evaluation_identity.live_addendum_path)) == 2

    rendered = capsys.readouterr().out
    assert "terminal_status=" in rendered
    assert "bounded_failure_code=RESULT_PACKET_" + "MISSING" in rendered
    assert "fictional-private-stdout-sentinel" not in rendered
    assert "fictional-private-stderr-sentinel" not in rendered


@pytest.mark.parametrize(
    ("failure_site", "expected_code", "expected_child_calls"),
    (
        ("root", "REPOSITORY_ROOT_RESOLUTION_FAILED", 0),
        ("addendum_path", "LIVE_ADDENDUM_PATH_REJECTED", 0),
        ("addendum_read", "LIVE_ADDENDUM_READ_FAILED", 0),
        ("repository_sha", "REPOSITORY_SHA_MISMATCH", 0),
        ("path_preparation", "HANDSHAKE_PATH_REJECTED", 0),
        ("child_create", "CHILD_PROCESS_CREATE_FAILED", 1),
    ),
)
def test_known_pre_child_stop_codes_preserve_exact_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_site: str,
    expected_code: str,
    expected_child_calls: int,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)
    child_calls: list[object] = []

    def child_run(*args: object, **kwargs: object) -> None:
        child_calls.append((args, kwargs))
        raise OSError("fictional-private-child-create-sentinel")

    if failure_site == "root":
        monkeypatch.setattr(
            launcher,
            "_repository_root",
            _raise(OSError("fictional-private-root-sentinel")),
        )
    elif failure_site == "addendum_path":
        monkeypatch.setattr(
            launcher,
            "_normalize_addendum_path",
            _raise(launcher.OwnerSpecificAuthorizationError("fictional-private-path-sentinel")),
        )
    elif failure_site == "addendum_read":
        monkeypatch.setattr(
            launcher,
            "load_json_object",
            _raise(launcher.OwnerSpecificAuthorizationError("fictional-private-read-sentinel")),
        )
    elif failure_site == "repository_sha":
        monkeypatch.setattr(
            launcher,
            "current_repository_sha",
            lambda *, repository_root: "b" * 40,
        )
    elif failure_site == "path_preparation":
        monkeypatch.setattr(
            launcher,
            "_prepare_paths",
            _raise(launcher._LauncherStop("HANDSHAKE_PATH_REJECTED")),
        )
    elif failure_site != "child_create":
        raise AssertionError(f"unhandled failure site: {failure_site}")
    monkeypatch.setattr(launcher.subprocess, "Popen", child_run)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == expected_code
    assert outcome.facts.child_process_created is False
    assert outcome.facts.evaluator_entry_posture == "FALSE"
    assert outcome.facts.manifest_consumption_posture == "ZERO_PRE_CHILD"
    assert outcome.facts.cost_posture == "EXACT_ZERO_PRE_CHILD"
    assert outcome.facts.planner_calls == 0
    assert outcome.facts.total_broker_calls == 0
    assert outcome.facts.observed_cost_usd == "0"
    assert len(child_calls) == expected_child_calls
    assert "fictional-private" not in repr(outcome)


def test_invalid_authorization_round_trip_stops_before_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)
    addendum_path = root / authorization.evaluation_identity.live_addendum_path
    private_sentinel = "fictional-private-authorization-sentinel"
    addendum_path.write_text(
        json.dumps({"fixture": private_sentinel}),
        encoding="utf-8",
    )
    child_calls: list[object] = []
    monkeypatch.setattr(
        launcher.subprocess,
        "Popen",
        lambda *args, **kwargs: child_calls.append((args, kwargs)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "AUTHORIZATION_VALIDATION_FAILED"
    assert outcome.facts.child_process_created is False
    assert outcome.facts.evaluator_entry_posture == "FALSE"
    assert outcome.attestation_relative is None
    assert private_sentinel not in repr(outcome)
    assert child_calls == []


def test_launcher_never_loads_private_scenario_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    scenario_path = root / authorization.evaluation_identity.scenario_packet_path
    private_sentinel = "fictional-private-scenario-sentinel"
    scenario_path.write_text(
        json.dumps({"fixture": private_sentinel}),
        encoding="utf-8",
    )
    production_load = launcher.load_json_object
    loaded_paths: list[Path] = []

    def tracked_load(path: Path) -> dict[str, Any]:
        loaded_paths.append(path)
        assert path == root / authorization.evaluation_identity.live_addendum_path
        return production_load(path)

    monkeypatch.setattr(launcher, "load_json_object", tracked_load)
    fake_popen, _ = _fake_child(
        root=root,
        argv=argv,
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "RESULT_PACKET_MISSING"
    assert outcome.facts.child_process_created is True
    assert private_sentinel not in repr(outcome)
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    assert private_sentinel not in json.dumps(packet, sort_keys=True)
    assert loaded_paths == [root / authorization.evaluation_identity.live_addendum_path]


def test_invalid_handshake_maps_to_its_own_post_child_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, _ = _launcher_fixture(tmp_path, monkeypatch)

    def popen(
        command: list[str],
        **kwargs: Any,
    ) -> _FakeChildProcess:
        del command, kwargs
        startup_path = root / (authorization.evaluation_identity.output_packet_path + ".startup.json")
        startup_path.write_text(
            '{"fixture":"fictional-private-handshake-sentinel"}',
            encoding="utf-8",
        )
        return _FakeChildProcess(
            exit_code=0,
            stdout="fictional-private-stdout-sentinel",
            stderr="fictional-private-stderr-sentinel",
            on_communicate=None,
        )

    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == "EVALUATOR_HANDSHAKE_INVALID"
    assert outcome.facts.terminal_status == "STOPPED_PRE_EVALUATOR_ENTRY"
    assert outcome.facts.child_process_created is True
    assert outcome.facts.evaluator_entry_posture == "UNKNOWN"
    assert outcome.facts.planner_calls is None
    assert outcome.facts.observed_cost_usd is None
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    assert "fictional-private-handshake-sentinel" not in json.dumps(
        packet,
        sort_keys=True,
    )


@pytest.mark.parametrize(
    ("failure_kind", "expected_code"),
    (
        ("invalid_result", "RESULT_PACKET_VALIDATION_FAILED"),
        ("digest", "RESULT_PACKET_DIGEST_FAILED"),
    ),
)
def test_observed_unvalidated_result_never_implies_exact_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
    expected_code: str,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    result_path = root / authorization.evaluation_identity.output_packet_path

    def write_invalid_result() -> None:
        result_path.write_text(
            '{"fixture":"fictional-private-result-sentinel"}',
            encoding="utf-8",
        )

    fake_popen, _ = _fake_child(
        root=root,
        argv=argv,
        on_communicate=write_invalid_result,
    )
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    if failure_kind == "digest":
        monkeypatch.setattr(
            launcher,
            "load_validated_result_metadata",
            _raise(attestation.ResultPacketDigestError("synthetic digest fault")),
        )
    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.bounded_failure_code == expected_code
    assert outcome.facts.terminal_status == "STOPPED_DURING_RESULT_VALIDATION"
    assert outcome.facts.child_process_created is True
    assert outcome.facts.evaluator_entry_posture == "TRUE"
    assert outcome.facts.result_packet_created is True
    assert outcome.facts.result_packet_sha256 is None
    assert outcome.facts.manifest_consumption_posture == ("UNKNOWN_AFTER_EVALUATOR_ENTRY")
    assert outcome.facts.cost_posture == "UNKNOWN_AFTER_EVALUATOR_ENTRY"
    assert outcome.facts.total_broker_calls is None
    assert outcome.facts.observed_cost_usd is None
    packet = attestation.load_json_object(root / str(outcome.attestation_relative))
    assert "fictional-private-result-sentinel" not in json.dumps(
        packet,
        sort_keys=True,
    )


def test_late_attestation_collision_maps_to_safe_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authorization, _, argv = _launcher_fixture(tmp_path, monkeypatch)
    fake_run, _ = _fake_child(root=root, argv=argv)
    monkeypatch.setattr(launcher.subprocess, "Popen", fake_run)
    private_sentinel = "fictional-private-attestation-write-sentinel"
    monkeypatch.setattr(
        launcher,
        "write_stop_attestation",
        _raise(FileExistsError(private_sentinel)),
    )

    outcome = launcher.execute_launcher(("--live-addendum", authorization.evaluation_identity.live_addendum_path))

    assert outcome.facts.terminal_status == "STOPPED_DURING_ATTESTATION_WRITE"
    assert outcome.facts.bounded_failure_code == "ATTESTATION_WRITE_FAILED"
    assert outcome.facts.exception_class_code == "OS_ERROR"
    assert outcome.facts.exception_message_sha256 is not None
    assert private_sentinel not in repr(outcome)
    assert outcome.attestation_sha256 is None
