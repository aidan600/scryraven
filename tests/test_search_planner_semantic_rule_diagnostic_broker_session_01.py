"""Offline custody proof for the bounded Planner diagnostic broker session.

Mode: REPAIR.
Test class: phase_focus / offline_operator_boundary.
No test here opens a private environment file or contacts a provider.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import run_provider_proxy_broker_once as broker_helper
from scripts import run_search_planner_semantic_rule_diagnostic_broker_session as session
from scripts.evaluation import run_search_planner_semantic_rule_diagnostic as cli
from scripts.evaluation.search_planner_semantic_rule_diagnostic import (
    SearchPlannerSemanticRuleDiagnosticError,
)


def test_generic_broker_fuse_allows_exact_six_but_no_unbounded_value(
    tmp_path: Path,
) -> None:
    env = broker_helper.broker_environment(
        token="test-token",
        env_file_path=tmp_path / "private.env",
        maximum_requests=6,
        process_env={"PATH": "test"},
    )
    assert env["SCRYRAVEN_BROKER_MAX_REQUESTS"] == "6"
    with pytest.raises(broker_helper.ProviderExecutionOperatorError):
        broker_helper.broker_environment(
            token="test-token",
            env_file_path=tmp_path / "private.env",
            maximum_requests=7,
            process_env={"PATH": "test"},
        )


def test_session_passes_private_path_only_to_broker_and_marker_only_to_evaluator(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text("not-inspected-by-test", encoding="utf-8")
    seen: dict[str, Any] = {}
    process = SimpleNamespace(poll=lambda: None)

    monkeypatch.setattr(
        session.broker_helper,
        "normalize_environment_file_path",
        lambda value: Path(value),
    )
    monkeypatch.setattr(
        session.broker_helper,
        "generate_temporary_broker_token",
        lambda: "temporary-token",
    )

    def broker_environment(**kwargs: Any) -> dict[str, str]:
        seen["broker_environment"] = kwargs
        return {"broker": "environment"}

    monkeypatch.setattr(session.broker_helper, "broker_environment", broker_environment)
    monkeypatch.setattr(
        session.broker_helper,
        "start_tracked_broker",
        lambda **kwargs: seen.setdefault("start", kwargs) and process,
    )
    monkeypatch.setattr(
        session.broker_helper,
        "wait_for_broker_readiness",
        lambda *_args, **kwargs: seen.setdefault("readiness", kwargs),
    )
    monkeypatch.setattr(
        session.broker_helper,
        "client_environment",
        lambda **kwargs: {"client": "environment"},
    )
    monkeypatch.setattr(
        session.broker_helper,
        "stop_tracked_broker",
        lambda value: seen.setdefault("stopped", value),
    )

    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        seen["argv"] = argv
        seen["child_env"] = kwargs["env"]
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(session.subprocess, "run", fake_run)
    rc = session.main(
        [
            "--env-file",
            str(env_file),
            "--repository-sha",
            "a" * 40,
            "--cases-file",
            str(tmp_path / "cases.json"),
            "--output",
            str(tmp_path / "result.json"),
            "--confirm-live-evaluation",
        ]
    )

    assert rc == 0
    assert seen["broker_environment"]["env_file_path"] == env_file
    assert seen["broker_environment"]["maximum_requests"] == 6
    assert seen["child_env"] == {
        "client": "environment",
        "SCRYRAVEN_SEARCH_PLANNER_DIAGNOSTIC_BROKER_SESSION": "1",
    }
    assert "--execute" in seen["argv"]
    assert seen["stopped"] is process


def test_evaluator_cli_refuses_direct_execute_without_session_marker() -> None:
    with pytest.raises(SearchPlannerSemanticRuleDiagnosticError, match="broker"):
        cli.main(
            [
                "--execute",
                "--repository-sha",
                "a" * 40,
                "--cases-file",
                "not-read-before-session-check.json",
                "--output",
                "not-written-before-session-check.json",
            ]
        )
