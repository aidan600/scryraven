from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.evaluation import (
    run_analystos_model_origination_evaluation as compatibility_runner,
)
from scripts.evaluation import (
    run_search_planner_owner_specific_evaluation as cli,
)
from scripts.evaluation.search_planner_owner_specific_authorization import (
    GENERIC_BROKER_TRANSPORT_FACTORY_SPEC,
    OwnerSpecificAuthorizationError,
)
from tests.helpers.search_planner_owner_specific_fakes import (
    authorization_bundle,
)

REPOSITORY_SHA = "3a76a3a24efef5ee4bec2d43e301463b671f0d80"
ENTRYPOINT = (
    "scripts/evaluation/"
    "run_search_planner_owner_specific_evaluation.py"
)


def test_cli_plan_only_is_zero_live_and_needs_no_addendum(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    execution_calls: list[object] = []

    def forbidden_execute(**kwargs: Any) -> dict[str, Any]:
        execution_calls.append(kwargs)
        raise AssertionError("plan_only constructed an execution path")

    monkeypatch.setattr(
        cli,
        "current_repository_sha",
        lambda: REPOSITORY_SHA,
    )
    monkeypatch.setattr(
        cli,
        "execute_owner_specific_evaluation",
        forbidden_execute,
    )

    assert (
        cli.main(
            (
                ENTRYPOINT,
                "--execution-mode",
                "plan_only",
                "--repository-sha",
                REPOSITORY_SHA,
            )
        )
        == 0
    )

    packet = json.loads(capsys.readouterr().out)
    assert packet["execution_mode"] == "plan_only"
    assert set(packet["owner_results"].values()) == {"NOT_RUN"}
    assert packet["call_counts"]["broker_calls"] == 0
    assert packet["transport_created"] is False
    assert packet["credentials_accessed"] is False
    assert packet["raw_material_retained"] is False
    assert execution_calls == []


def test_cli_execute_requires_complete_authority_before_file_or_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_reads: list[object] = []
    execution_calls: list[object] = []

    def forbidden_read(path: Path) -> dict[str, Any]:
        file_reads.append(path)
        raise AssertionError("incomplete execute read an addendum")

    def forbidden_execute(**kwargs: Any) -> dict[str, Any]:
        execution_calls.append(kwargs)
        raise AssertionError("incomplete execute constructed transport")

    monkeypatch.setattr(
        cli,
        "current_repository_sha",
        lambda: REPOSITORY_SHA,
    )
    monkeypatch.setattr(cli, "load_json_object", forbidden_read)
    monkeypatch.setattr(
        cli,
        "execute_owner_specific_evaluation",
        forbidden_execute,
    )

    with pytest.raises(
        OwnerSpecificAuthorizationError,
        match="execute requires repository SHA, live addendum",
    ):
        cli.main(
            (
                ENTRYPOINT,
                "--execution-mode",
                "execute",
                "--repository-sha",
                REPOSITORY_SHA,
            )
        )

    assert file_reads == []
    assert execution_calls == []


def test_cli_loads_only_the_exact_canonical_execute_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    authorization, scenario, argv = authorization_bundle(
        repository_root=tmp_path,
        repository_sha=REPOSITORY_SHA,
    )
    addendum = (
        tmp_path
        / authorization.evaluation_identity.live_addendum_path
    )
    scenario_path = (
        tmp_path
        / authorization.evaluation_identity.scenario_packet_path
    )
    addendum.parent.mkdir(parents=True, exist_ok=True)
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    addendum.write_text(
        json.dumps(authorization.to_packet()),
        encoding="utf-8",
    )
    scenario_path.write_text(
        json.dumps(scenario.to_packet()),
        encoding="utf-8",
    )
    captured: dict[str, Any] = {}

    def fake_execute(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "execution_mode": "execute",
            "transport_created": False,
        }

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(
        cli,
        "current_repository_sha",
        lambda: REPOSITORY_SHA,
    )
    monkeypatch.setattr(
        cli,
        "execute_owner_specific_evaluation",
        fake_execute,
    )

    assert cli.main(argv) == 0
    assert captured["actual_argv"] == argv
    assert (
        captured["authorization"]
        .evaluation_identity.transport_factory_spec
        == GENERIC_BROKER_TRANSPORT_FACTORY_SPEC
    )
    assert captured["scenario_packet"].sha256 == scenario.sha256
    assert json.loads(capsys.readouterr().out) == {
        "execution_mode": "execute",
        "transport_created": False,
    }


def test_cli_has_no_transport_selector_or_direct_provider_path() -> None:
    source = Path(cli.__file__).read_text(encoding="utf-8")
    orchestration_source = Path(
        "scripts/evaluation/"
        "search_planner_owner_specific_orchestration.py"
    ).read_text(encoding="utf-8")

    with pytest.raises(SystemExit):
        cli.main(
            (
                ENTRYPOINT,
                "--transport-factory",
                "direct-openai",
            )
        )

    assert "--transport-factory" not in source
    assert "openai" not in source.casefold()
    assert "tests." not in source
    assert "tests." not in orchestration_source
    assert "create_brokered_model_route_transport" in orchestration_source


def test_compatibility_runner_execute_remains_retired() -> None:
    with pytest.raises(
        compatibility_runner.EvaluationConfigurationError,
        match="retired before addendum or transport access",
    ):
        compatibility_runner.main(
            (
                "scripts/evaluation/"
                "run_analystos_model_origination_evaluation.py",
                "--evaluation-pass",
                "planner_only",
                "--execution-mode",
                "execute",
                "--live-addendum",
                "must-not-be-read.json",
            )
        )
