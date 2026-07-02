from __future__ import annotations

import ast
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from core.ordinary_live_main_runkernel_coverage_runtime import (
    ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY,
)
from core.product_model_route_config import LIVE_SEMANTIC_COVERAGE_STATUS_FLAG
from proplex.ordinary_live_entrypoint_dry_run import (
    ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG,
    format_ordinary_live_entrypoint_dry_run_status,
)

ROOT = Path(__file__).resolve().parents[1]
QUERY = "What is the official current permit threshold for the example program?"
PRODUCT_FILES = (
    ROOT / "proplex" / "__main__.py",
    ROOT / "proplex" / "ordinary_live_entrypoint_dry_run.py",
)
OFFLINE_PROVIDER_ENV_KEYS = (
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "LINKUP_API_KEY",
    "EXA_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)
IMPORT_TIME_TIMEOUT_ENV_KEYS = (
    "TAVILY_SEARCH_TIMEOUT_SEC",
    "LINKUP_SEARCH_TIMEOUT_SEC",
    "BRAVE_SEARCH_TIMEOUT_SEC",
    "SERPER_SEARCH_TIMEOUT_SEC",
    "EXA_SEARCH_TIMEOUT_SEC",
)


def test_normal_cli_startup_loads_dotenv_before_search_provider_import(
    tmp_path: Path,
) -> None:
    result = _run_search_provider_startup_probe(
        tmp_path,
        argv_after_query=[],
    )

    assert result["search_providers_imported_by_cli_core_imports"] is True
    assert result["brave_search_timeout_sec"] == 17.0


def test_dry_run_startup_skips_dotenv_before_search_provider_import(
    tmp_path: Path,
) -> None:
    result = _run_search_provider_startup_probe(
        tmp_path,
        argv_after_query=[ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG],
    )

    assert result["search_providers_imported_by_cli_core_imports"] is True
    assert result["brave_search_timeout_sec"] == 8.0


def test_semantic_coverage_status_dry_run_startup_skips_dotenv(
    tmp_path: Path,
) -> None:
    result = _run_search_provider_startup_probe(
        tmp_path,
        argv_after_query=[LIVE_SEMANTIC_COVERAGE_STATUS_FLAG],
    )

    assert result["search_providers_imported_by_cli_core_imports"] is True
    assert result["brave_search_timeout_sec"] == 8.0


def test_actual_proplex_entrypoint_reaches_main_runkernel_coverage_dry_run() -> None:
    env = os.environ.copy()
    for key in OFFLINE_PROVIDER_ENV_KEYS:
        env.pop(key, None)

    proc = subprocess.run(
        [sys.executable, "-m", "proplex", QUERY, ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ordinary-live dry-run reached main RunKernel coverage" in proc.stdout
    assert "ordinary entrypoint: python -m proplex" in proc.stdout
    assert "runtime consumer: core.pipeline_orchestrator.run_pipeline" in proc.stdout
    assert "main SemanticObservation admitted: true" in proc.stdout
    assert "main ComponentCoverage reduced: true" in proc.stdout
    assert "live calls: 0" in proc.stdout
    assert "output type: dry-run status, not live product behavior" in proc.stdout
    assert "official current Example Program permit threshold is 500" not in proc.stdout


def test_default_cli_runconfig_keeps_ordinary_live_dry_run_disabled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _import_cli_with_dotenv_disabled(monkeypatch)
    captured: dict[str, Any] = {}

    def fake_run_pipeline(config: Any, deps: Any, _status: Any, _accumulator: Any) -> Any:
        captured["config"] = config
        captured["deps"] = deps
        return SimpleNamespace(
            report="default report",
            execution_trace={},
            cost_snapshot={"total_calls": 0, "total_cost_usd": 0.0},
            latency_seconds=0.0,
        )

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "missing_required_api_keys", lambda **_kwargs: [])
    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        cli,
        "append_official_canonical_recovery_diagnostics_section",
        lambda report, _trace: report,
    )

    assert cli.main([QUERY]) == 0

    assert captured["config"].enable_ordinary_live_main_runkernel_coverage is False
    assert captured["deps"].ordinary_live_source_fetch_read is None
    out = capsys.readouterr()
    assert "default report" in out.out
    assert "ordinary-live dry-run reached main RunKernel coverage" not in out.out


def test_dry_run_cli_builds_enabled_runconfig_and_skips_live_key_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _import_cli_with_dotenv_disabled(monkeypatch)
    captured: dict[str, Any] = {}

    def fail_key_validation(**_kwargs: Any) -> list[str]:
        raise AssertionError("dry-run must not validate live provider keys")

    def fail_load_dotenv() -> None:
        raise AssertionError("dry-run must not load .env")

    def fake_run_pipeline(config: Any, deps: Any, _status: Any, _accumulator: Any) -> Any:
        captured["config"] = config
        captured["deps"] = deps
        return SimpleNamespace(report="SHOULD_NOT_PRINT_REPORT", execution_trace=_success_trace())

    monkeypatch.setattr(cli, "load_dotenv", fail_load_dotenv)
    monkeypatch.setattr(cli, "missing_required_api_keys", fail_key_validation)
    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)

    assert cli.main([QUERY, ORDINARY_LIVE_ENTRYPOINT_DRY_RUN_FLAG]) == 0

    config = captured["config"]
    deps = captured["deps"]
    assert config.query == QUERY
    assert config.enable_ordinary_live_main_runkernel_coverage is True
    assert config.ordinary_live_candidate_handoff_results
    assert callable(deps.ordinary_live_source_fetch_read)
    out = capsys.readouterr()
    assert "ordinary-live dry-run reached main RunKernel coverage" in out.out
    assert "SHOULD_NOT_PRINT_REPORT" not in out.out


def test_dry_run_status_surfaces_named_blocker_when_trace_is_missing() -> None:
    status = format_ordinary_live_entrypoint_dry_run_status(execution_trace={})

    assert "ordinary-live dry-run blocked" in status
    assert "blocker: ordinary_entrypoint_visibility_not_supported" in status
    assert "output type: dry-run blocker, not live product behavior" in status


def test_product_dry_run_code_does_not_import_scripts_or_test_helpers() -> None:
    for path in PRODUCT_FILES:
        source = path.read_text(encoding="utf-8")
        imported = _imports(path)
        assert "scripts/ag_" not in source
        assert "tests/helpers/offline_ordinary_pipeline.py" not in source
        assert "tests.helpers.offline_ordinary_pipeline" not in imported
        assert not any(name == "scripts" or name.startswith("scripts.") for name in imported)


def test_dry_run_status_keeps_closed_surface_flags_visible() -> None:
    status = format_ordinary_live_entrypoint_dry_run_status(
        execution_trace=_success_trace(),
    )

    assert "Sufficiency/FAP/Author closed for ordinary-live coverage: true" in status
    assert "live calls: 0" in status
    assert "output type: dry-run status, not live product behavior" in status


def _success_trace() -> dict[str, Any]:
    return {
        ORDINARY_LIVE_MAIN_RUNKERNEL_COVERAGE_TRACE_KEY: {
            "ran": True,
            "failed_closed": False,
            "main_semantic_observation_admitted_count": 1,
            "main_component_coverage_reduced_count": 1,
            "provider_search_calls": 0,
            "search_calls": 0,
            "broker_calls": 0,
            "fetch_read_calls": 0,
            "model_calls": 0,
            "retrieval_calls": 0,
            "closed_surface_flags": {
                "sufficiency_readiness_reduced": False,
                "fap_created": False,
                "author_invoked": False,
                "answer_text_created": False,
                "product_correctness_claimed": False,
            },
        }
    }


def _run_search_provider_startup_probe(
    tmp_path: Path,
    *,
    argv_after_query: list[str],
) -> dict[str, Any]:
    (tmp_path / ".env").write_text(
        "BRAVE_SEARCH_TIMEOUT_SEC=17\n",
        encoding="utf-8",
    )
    probe = tmp_path / "startup_probe.py"
    # python-dotenv searches from cwd when a debugger trace is active; this keeps
    # the probe on the test-created .env instead of any repository-local file.
    probe.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "import json",
                "import sys",
                f"sys.path.insert(0, {str(ROOT)!r})",
                f"sys.argv = ['proplex', 'probe query', *{argv_after_query!r}]",
                "sys.settrace(lambda *_args: None)",
                "try:",
                "    import proplex.__main__  # noqa: F401",
                "finally:",
                "    sys.settrace(None)",
                "already_imported = 'core.search_providers' in sys.modules",
                "if already_imported:",
                "    search_providers = sys.modules['core.search_providers']",
                "else:",
                "    import core.search_providers as search_providers",
                "print(json.dumps({",
                "    'search_providers_imported_by_cli_core_imports': already_imported,",
                "    'brave_search_timeout_sec': search_providers.BRAVE_SEARCH_TIMEOUT_SEC,",
                "}))",
                "",
            )
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(probe)],
        cwd=tmp_path,
        env=_startup_probe_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def _startup_probe_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (*OFFLINE_PROVIDER_ENV_KEYS, *IMPORT_TIME_TIMEOUT_ENV_KEYS):
        env.pop(key, None)
    env.pop("PYTHON_DOTENV_DISABLED", None)
    python_path = str(ROOT)
    if env.get("PYTHONPATH"):
        python_path = python_path + os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = python_path
    return env


def _import_cli_with_dotenv_disabled(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    return importlib.import_module("proplex.__main__")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported
