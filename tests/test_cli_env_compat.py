from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from proplex.__main__ import _parse_args
from proplex.env_aliases import pop_env_alias

_ROOT = Path(__file__).resolve().parents[1]


def test_scryraven_module_help_works_without_api_keys() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "scryraven", "--help"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ScryRaven" in proc.stdout
    assert "python -m proplex" in proc.stdout


def test_proplex_module_help_still_works_without_api_keys() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "proplex", "--help"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ScryRaven" in proc.stdout
    assert "python -m proplex" in proc.stdout


def test_scryraven_cli_env_aliases_win_over_legacy(monkeypatch) -> None:
    monkeypatch.setenv("SCRYRAVEN_FAST_PROVIDER", "Local (LM Studio)")
    monkeypatch.setenv("PROPLEX_FAST_PROVIDER", "OpenAI")
    monkeypatch.setenv("SCRYRAVEN_FAST_MODEL", "public-fast")
    monkeypatch.setenv("PROPLEX_FAST_MODEL", "legacy-fast")
    monkeypatch.setenv("SCRYRAVEN_SMART_PROVIDER", "OpenRouter")
    monkeypatch.setenv("PROPLEX_SMART_PROVIDER", "OpenAI")
    monkeypatch.setenv("SCRYRAVEN_SMART_MODEL", "public-smart")
    monkeypatch.setenv("PROPLEX_SMART_MODEL", "legacy-smart")
    monkeypatch.setenv("SCRYRAVEN_EMBED_PROVIDER", "OpenAI")
    monkeypatch.setenv("PROPLEX_EMBED_PROVIDER", "LegacyEmbed")
    monkeypatch.setenv("SCRYRAVEN_EMBED_MODEL", "public-embed")
    monkeypatch.setenv("PROPLEX_EMBED_MODEL", "legacy-embed")
    monkeypatch.setenv("SCRYRAVEN_LOCAL_URL", "http://public.local/v1")
    monkeypatch.setenv("PROPLEX_LOCAL_URL", "http://legacy.local/v1")

    args = _parse_args(["offline query"])

    assert args.fast_provider == "Local (LM Studio)"
    assert args.fast_model == "public-fast"
    assert args.smart_provider == "OpenRouter"
    assert args.smart_model == "public-smart"
    assert args.embed_provider == "OpenAI"
    assert args.embed_model == "public-embed"
    assert args.local_url == "http://public.local/v1"


def test_legacy_cli_env_aliases_still_work(monkeypatch) -> None:
    monkeypatch.setenv("PROPLEX_FAST_PROVIDER", "LegacyFastProvider")
    monkeypatch.setenv("PROPLEX_FAST_MODEL", "legacy-fast")
    monkeypatch.setenv("PROPLEX_SMART_PROVIDER", "LegacySmartProvider")
    monkeypatch.setenv("PROPLEX_SMART_MODEL", "legacy-smart")
    monkeypatch.setenv("PROPLEX_EMBED_PROVIDER", "LegacyEmbedProvider")
    monkeypatch.setenv("PROPLEX_EMBED_MODEL", "legacy-embed")
    monkeypatch.setenv("PROPLEX_LOCAL_URL", "http://legacy.local/v1")

    args = _parse_args(["offline query"])

    assert args.fast_provider == "LegacyFastProvider"
    assert args.fast_model == "legacy-fast"
    assert args.smart_provider == "LegacySmartProvider"
    assert args.smart_model == "legacy-smart"
    assert args.embed_provider == "LegacyEmbedProvider"
    assert args.embed_model == "legacy-embed"
    assert args.local_url == "http://legacy.local/v1"


def test_streamlit_scripted_launch_public_alias_wins_over_legacy() -> None:
    env = {
        "SCRYRAVEN_RUN_QUERY": "public query",
        "PROPLEX_RUN_QUERY": "legacy query",
        "SCRYRAVEN_RUN_MODE": "Deep",
        "PROPLEX_RUN_MODE": "Fast",
    }

    assert pop_env_alias("SCRYRAVEN_RUN_QUERY", "PROPLEX_RUN_QUERY", environ=env) == "public query"
    assert pop_env_alias("SCRYRAVEN_RUN_MODE", "PROPLEX_RUN_MODE", environ=env) == "Deep"
    assert env == {}


def test_streamlit_scripted_launch_legacy_alias_still_works() -> None:
    env = {
        "PROPLEX_RUN_QUERY": "legacy query",
        "PROPLEX_RUN_MODE": "Fast",
    }

    assert pop_env_alias("SCRYRAVEN_RUN_QUERY", "PROPLEX_RUN_QUERY", environ=env) == "legacy query"
    assert pop_env_alias("SCRYRAVEN_RUN_MODE", "PROPLEX_RUN_MODE", environ=env) == "Fast"
    assert env == {}
