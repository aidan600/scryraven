"""INTEGRATION-STAGING: D-prime launcher consumes product config boundary.

Harness label: INTEGRATION-STAGING
Ordinary product path guarded or fed: scripts/run_dprime_real_model_review_once.py
for DPRIME-REAL-MODEL-REVIEW-RUN-01B.
Runtime consumer: the next D-prime real model-review operator run.
Why ordinary product-path work cannot be done directly: this phase is not
licensed to call a real model; tests inject config posture and inspect safe
preflight/status wiring only.
Integration deadline: DPRIME-REAL-MODEL-REVIEW-RUN-01B.
Exit condition: convert to PRODUCT-PATH-REGRESSION after the real run consumes
the launcher, or retire the launcher if the operation moves.
Why this is not a shadow product path: the launcher calls the existing product
semantic coverage status builder and D-prime adapter when real-run mode is
explicitly selected; preflight does not emulate model review.
Forbidden interpretation: passing tests do not prove live validation, model
quality, semantic support, citations, answer readiness, answer text, or product
correctness.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import scripts.run_dprime_real_model_review_once as launcher
from core.dprime_product_smart_one_shot_transport import (
    BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT,
    PRODUCT_CONFIG_INITIALIZATION_BOUNDARY,
)
from core.product_model_route_config import ProductModelRouteConfigInitialization

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_dprime_real_model_review_once.py"
CLI = ROOT / "proplex" / "__main__.py"
TRANSPORT = ROOT / "core" / "dprime_product_smart_one_shot_transport.py"
_OPENAI_ENV_NAME = "OPENAI_" + "API_" + "KEY"
_MINIMAL_SUBPROCESS_ENV_KEYS = (
    "APPDATA",
    "COMSPEC",
    "HOME",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
)


def test_direct_script_preflight_works_without_external_pythonpath() -> None:
    env = _minimal_subprocess_env()
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "What is the adult U.S. passport book renewal fee?",
            "--credential-preflight-only",
            "--no-secret-values",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "D-prime real model-review credential preflight" in output
    assert (
        "product config boundary: "
        "core.product_model_route_config.initialize_product_model_route_config"
    ) in output
    assert "OPENAI_API_KEY present in current process: false" in output
    assert "real model call performed: false" in output
    assert "raw prompt retained: false" in output
    assert "raw model response retained: false" in output
    assert "provider payload retained: false" in output
    assert "raw_prompt" not in output.casefold()
    assert "raw_model_response" not in output.casefold()
    assert "provider_payload" not in output.casefold()
    assert "api_key:" not in output.casefold()
    assert _OPENAI_ENV_NAME not in env
    assert "PYTHONPATH" not in env


def test_launcher_and_ordinary_cli_share_product_config_boundary() -> None:
    assert "initialize_product_model_route_config" in _imported_names(CLI)
    assert "initialize_product_model_route_config" in _imported_names(SCRIPT)
    assert PRODUCT_CONFIG_INITIALIZATION_BOUNDARY in TRANSPORT.read_text(
        encoding="utf-8"
    )


def test_credential_preflight_invokes_boundary_and_prints_booleans_only(
    capsys: Any,
) -> None:
    calls: list[list[str]] = []

    def fake_initialize(
        argv: Sequence[str] | None,
    ) -> ProductModelRouteConfigInitialization:
        calls.append(list(argv or []))
        return ProductModelRouteConfigInitialization(
            dotenv_helper_invoked=True,
            dotenv_skipped_for_status_dry_run=False,
            dotenv_result=True,
            openai_api_key_present=True,
        )

    rc = launcher.main(
        [
            "example query",
            "--credential-preflight-only",
            "--no-secret-values",
        ],
        initialize_config=fake_initialize,
        environ={_OPENAI_ENV_NAME: "placeholder-value-must-not-print"},
    )

    assert rc == 0
    assert calls == [["example query", "--credential-preflight-only", "--no-secret-values"]]
    out = capsys.readouterr().out
    assert "dotenv helper invoked: true" in out
    assert "dotenv skipped for status dry-run: false" in out
    assert "OPENAI_API_KEY present in current process: true" in out
    assert "placeholder-value-must-not-print" not in out
    assert "api_key:" not in out.casefold()
    assert "product_model_role: smart" in out
    assert "product_route_kind: smart_model_route" in out
    assert "OpenAI / gpt-5.4" in out
    assert "real model call performed: false" in out


def test_credential_preflight_requires_no_secret_values(capsys: Any) -> None:
    rc = launcher.main(
        ["example query", "--credential-preflight-only"],
        initialize_config=lambda _argv: ProductModelRouteConfigInitialization(),
        environ={_OPENAI_ENV_NAME: "placeholder-value-must-not-print"},
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert "requires --no-secret-values" in captured.err
    assert "placeholder-value-must-not-print" not in captured.out
    assert "placeholder-value-must-not-print" not in captured.err


def test_launcher_defaults_to_product_smart_route_from_config_aliases(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("SCRYRAVEN_SMART_PROVIDER", "OpenAI")
    monkeypatch.setenv("SCRYRAVEN_SMART_MODEL", "gpt-5.4")
    init = ProductModelRouteConfigInitialization(dotenv_helper_invoked=True)
    args = launcher._parse_args(["query"])
    payload = launcher.build_credential_preflight_payload(
        args=args,
        init=init,
        environ={},
    )

    assert payload["product_model_role"] == "smart"
    assert payload["product_route_kind"] == "smart_model_route"
    assert payload["configured_smart_provider"] == "OpenAI"
    assert payload["configured_smart_model"] == "gpt-5.4"


def test_launcher_boundary_and_license_do_not_select_provider_model_directly() -> None:
    boundary = launcher.build_dprime_real_run_provider_boundary()
    license_ref = launcher.build_dprime_real_run_license()

    assert boundary["provider_model_selection_status"] == "approval_ref_present"
    assert boundary["provider_model_approval_ref"]
    assert "provider" not in boundary
    assert "model" not in boundary
    assert license_ref["callable_kind"] == "real_one_shot"
    assert license_ref["retry_policy"] == "forbidden"
    assert license_ref["max_model_review_calls"] == 1
    assert "provider" not in license_ref
    assert "model" not in license_ref


def test_launcher_does_not_run_without_preflight_or_explicit_real_run(
    capsys: Any,
) -> None:
    rc = launcher.main(
        ["example query"],
        initialize_config=lambda _argv: ProductModelRouteConfigInitialization(),
        environ={},
    )

    assert rc == 2
    assert "--run-real-model-review only in the licensed phase" in capsys.readouterr().err


def test_unsupported_route_blocker_constant_remains_available() -> None:
    assert BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT == (
        "BLOCKED_PRODUCT_SMART_MODEL_ROUTE_CANNOT_ENFORCE_DPRIME_ONE_SHOT"
    )


def test_launcher_static_imports_avoid_broad_live_surfaces() -> None:
    forbidden_imports = {
        "core.llm",
        "core.pipeline_orchestrator",
        "core.retrieval",
        "core.retrieval_dispatch_runtime",
        "core.routing_runtime",
        "core.search_providers",
        "requests",
        "subprocess",
    }
    imports = _imports(SCRIPT)
    assert imports.isdisjoint(forbidden_imports)
    calls = _call_names(SCRIPT)
    assert "ask_model" not in calls
    assert "responses.create" not in calls
    assert "open" not in calls


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(alias.asname or alias.name for alias in node.names)
    return imported


def _call_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _expression_name(node.func)
            if call_name:
                calls.add(call_name)
    return calls


def _expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _expression_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _minimal_subprocess_env() -> dict[str, str]:
    env = {
        key: value
        for key in _MINIMAL_SUBPROCESS_ENV_KEYS
        if (value := os.environ.get(key))
    }
    env.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "SCRYRAVEN_SMART_PROVIDER": "OpenAI",
            "SCRYRAVEN_SMART_MODEL": "gpt-5.4",
        }
    )
    env.pop("PYTHONPATH", None)
    env.pop(_OPENAI_ENV_NAME, None)
    return env
