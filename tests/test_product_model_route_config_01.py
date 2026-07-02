"""PRODUCT-PATH-REGRESSION: shared product model-route config boundary.

Harness label: PRODUCT-PATH-REGRESSION
Ordinary product path guarded or fed: core.product_model_route_config.initialize_product_model_route_config
Runtime consumer: ordinary python -m proplex product model-route initialization
and D-prime one-shot launcher preflight.
Why ordinary product-path work cannot be done directly: this is the shared
product boundary itself; tests use a temporary fake .env and safe status only.
Integration deadline: current phase.
Exit condition: keep while product model-route consumers rely on this shared
config boundary for dotenv and credential-presence posture.
Why this is not a shadow product path: it calls the shared product config
boundary directly rather than creating a separate credential loader.
Forbidden interpretation: this does not prove live provider access, model
quality, semantic support, citation readiness, answer text, or product
correctness.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import core.product_model_route_config as product_config

ROOT = Path(__file__).resolve().parents[1]
_OPENAI_ENV_NAME = "OPENAI_" + "API_" + "KEY"
_PLACEHOLDER_SECRET = "placeholder-value-must-not-print"


def test_default_dotenv_loader_accepts_utf8_bom_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        f"{_OPENAI_ENV_NAME}={_PLACEHOLDER_SECRET}\n",
        encoding="utf-8-sig",
    )
    helper = (
        "import json\n"
        "from core.product_model_route_config import "
        "initialize_product_model_route_config\n"
        "status = initialize_product_model_route_config(argv=[]).to_safe_status()\n"
        "print(json.dumps(status, sort_keys=True))\n"
    )
    env = _minimal_subprocess_env()
    env["PYTHONPATH"] = str(ROOT)

    result = subprocess.run(
        [sys.executable, "-c", helper],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert _PLACEHOLDER_SECRET not in result.stdout
    assert _PLACEHOLDER_SECRET not in result.stderr
    status = json.loads(result.stdout)
    assert status["dotenv_helper_invoked"] is True
    assert status["dotenv_skipped_for_status_dry_run"] is False
    assert status["dotenv_result"] is True
    assert status["OPENAI_API_KEY_present"] is True
    assert _OPENAI_ENV_NAME not in env


def test_status_dry_run_still_skips_dotenv_loader(monkeypatch: object) -> None:
    def fail_load_dotenv() -> None:
        raise AssertionError("status dry-run must skip dotenv")

    status = product_config.initialize_product_model_route_config(
        argv=[product_config.LIVE_SEMANTIC_COVERAGE_STATUS_FLAG],
        load_dotenv_func=fail_load_dotenv,
        environ={},
    )

    assert status.dotenv_helper_invoked is False
    assert status.dotenv_skipped_for_status_dry_run is True
    assert status.dotenv_result is None
    assert status.openai_api_key_present is False


def test_injected_dotenv_loader_still_requires_no_kwargs() -> None:
    calls = 0

    def fake_load_dotenv() -> bool:
        nonlocal calls
        calls += 1
        return True

    status = product_config.initialize_product_model_route_config(
        argv=[],
        load_dotenv_func=fake_load_dotenv,
        environ={_OPENAI_ENV_NAME: "present-but-not-returned"},
    )

    assert calls == 1
    safe = status.to_safe_status()
    assert safe["OPENAI_API_KEY_present"] is True
    assert "present-but-not-returned" not in json.dumps(safe)


def _minimal_subprocess_env() -> dict[str, str]:
    keys = (
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
    env = {key: value for key in keys if (value := os.environ.get(key))}
    for key in tuple(env):
        if key.upper().startswith(("OPENAI_", "SCRYRAVEN_", "PROPLEX_")):
            env.pop(key, None)
    return env
