"""Offline checks for the intentionally non-executable reset foundation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_namespace_has_no_current_executable_entrypoint() -> None:
    assert (ROOT / "scryraven" / "__init__.py").is_file()
    assert not (ROOT / "scryraven" / "__main__.py").exists()
    assert not (ROOT / "app.py").exists()
