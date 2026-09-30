"""Make the repository root importable for focused offline tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def isolated_user_model_configuration(tmp_path, monkeypatch):
    """Offline tests never consume the operator's real model settings."""
    from scryraven import model

    monkeypatch.setattr(model, "user_model_config_path", lambda: tmp_path / "user-model_roles.json")
    # The Windows forensic launcher starts a separate Python process.
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "user-data"))
